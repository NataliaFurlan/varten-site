#!/usr/bin/env python3
"""Promote an exact, validated dev commit without changing the working branch."""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request


def run(args, cwd, capture=False, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if result.returncode:
        # Do not echo remote URLs, environment or secrets on errors.
        raise RuntimeError(f"Falhou: {args[0]} {args[1] if len(args) > 1 else ''} (código {result.returncode}).")
    return result.stdout.strip() if capture else None


def git(root, *args):
    return run(['git', *args], root, capture=True)


def resolve(root, ref):
    result = subprocess.run(['git', 'rev-parse', '--verify', ref + '^{commit}'],
                            cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.strip() if result.returncode == 0 else None


def ancestor(root, older, newer):
    return subprocess.run(['git', 'merge-base', '--is-ancestor', older, newer], cwd=root).returncode == 0


def validate_artifact(kind, directory):
    if kind in ('static', 'portal'):
        if not (directory / 'index.html').is_file():
            raise RuntimeError('Artefato web sem index.html.')
    if kind == 'api' and not (directory / 'dist/main.js').is_file():
        raise RuntimeError('Build da API sem dist/main.js.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Mostrar a promoção; padrão, sem rede ou publicação.')
    mode.add_argument('--check', action='store_true', help='Atualizar referências e validar/buildar o commit dev em pasta temporária.')
    mode.add_argument('--publish', action='store_true', help='Validar e promover o commit dev para origin/prod.')
    parser.add_argument('--database-ready', action='store_true', help='Confirma que backup e migrations desta versão já foram conferidos em produção.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    config = json.loads((root / 'release.json').read_text())
    kind = config['kind']
    source, destination, remote = 'dev', 'prod', 'origin'
    if not resolve(root, 'refs/heads/dev'):
        raise RuntimeError('Ainda não existe dev local. Crie dev a partir da branch de desenvolvimento e registre seus commits antes de promover.')
    commit = resolve(root, 'refs/heads/dev')
    print(f"Projeto: {config['name']} | dev: {commit[:12]} | destino: origin/prod", flush=True)
    if not args.check and not args.publish:
        baseline = resolve(root, 'refs/remotes/origin/prod') or resolve(root, 'refs/remotes/origin/main')
        print('Plano local; referências remotas podem estar desatualizadas.')
        if baseline:
            print(git(root, 'log', '--oneline', baseline + '..' + commit) or 'Sem novos commits.')
        print('Publicação real exige árvore limpa, dev enviada ao origin, verificações e configuração de hospedagem.')
        return
    if git(root, 'status', '--porcelain'):
        raise RuntimeError('Há alterações sem commit. Registre ou guarde suas alterações antes de validar/publicar.')
    # Fetch and prune to avoid using a deleted or stale remote production branch.
    run(['git', 'fetch', '--prune', remote], root)
    if resolve(root, 'refs/remotes/origin/dev') != commit:
        raise RuntimeError('dev local difere de origin/dev. Sincronize a versão validada antes de continuar.')
    production = resolve(root, 'refs/remotes/origin/prod')
    baseline = production or resolve(root, 'refs/remotes/origin/main')
    if not baseline:
        raise RuntimeError('Sem base de produção: confira origin/main ou origin/prod.')
    if not ancestor(root, baseline, commit):
        raise RuntimeError('dev e produção divergiram. Incorpore prod/main na dev e resolva os conflitos antes da promoção.')
    migrations = ''
    if kind == 'api':
        migrations = (git(root, 'diff', '--name-only', baseline, commit, '--', 'migrations')
                      if production else git(root, 'ls-tree', '-r', '--name-only', commit, '--', 'migrations'))
    if migrations:
        print('Migrations alteradas nesta versão:\n' + migrations, flush=True)
        if args.publish and not args.database_ready:
            raise RuntimeError('Confira backup e aplicação das migrations em produção; depois use --database-ready. O script não executa SQL automaticamente.')
    if kind == 'mobile' and production and commit != production:
        def version_code(ref):
            text = git(root, 'show', ref + ':pubspec.yaml')
            version = re.search(r'^version:\s*[^\s+]+\+(\d+)\s*$', text, re.MULTILINE)
            if not version:
                raise RuntimeError('pubspec.yaml precisa de version no formato 1.0.0+1.')
            return int(version.group(1))
        if version_code(commit) <= version_code(production):
            raise RuntimeError('Aumente o número após + em pubspec.yaml antes de publicar uma nova versão Android.')
    deploy = None
    if args.publish and kind != 'mobile':
        local_config = root / '.deploy.local.json'
        if not local_config.is_file():
            raise RuntimeError('Falta .deploy.local.json. Configure o destino real usando deploy.local.example.json; nada foi publicado.')
        deploy = json.loads(local_config.read_text())
        if deploy.get('method') == 'hostinger-git':
            if deploy.get('branch') != 'prod' or deploy.get('auto_deploy_confirmed') is not True:
                raise RuntimeError('Confirme no hPanel a publicação automática deste repositório pela branch prod.')
        elif deploy.get('method') == 'ssh' and kind in ('static', 'portal'):
            if not deploy.get('ssh_alias') or not str(deploy.get('web_root', '')).startswith('/') or deploy['web_root'] == '/':
                raise RuntimeError('Configure ssh_alias e web_root absoluto do site, diferente de /.')
            if any(c in deploy['ssh_alias'] for c in '\n\r :') or deploy['ssh_alias'].startswith('-'):
                raise RuntimeError('ssh_alias inválido; use um alias simples do ~/.ssh/config.')
            run(['ssh', '-o', 'BatchMode=yes', deploy['ssh_alias'], 'test -d ' + shlex.quote(deploy['web_root'])], root)
        else:
            raise RuntimeError('Configure hostinger-git ou ssh para sites/portal; API usa hostinger-git.')
        if not str(deploy.get('verification_url', '')).startswith('https://'):
            raise RuntimeError('Configure verification_url HTTPS para conferir a versão publicada.')
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    release_id = f"{timestamp}-{commit[:12]}"
    with tempfile.TemporaryDirectory(prefix='setta-release-') as temporary:
        work = Path(temporary) / 'source'
        work.mkdir()
        archive = Path(temporary) / 'source.tar'
        run(['git', 'archive', '--format=tar', '-o', str(archive), commit], root)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk() or member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise RuntimeError('Arquivo não suportado no pacote Git: ' + member.name)
            tar.extractall(work)
        # Copy ignored signing configuration only; never copy the development .env.
        environment = os.environ.copy()
        environment['RELEASE_COMMIT'] = commit
        if kind in ('api', 'portal'):
            environment.pop('NODE_ENV', None)
            run(['npm', 'ci'], work, env=environment)
            if kind == 'api':
                run(['npm', 'test', '--', '--runInBand'], work, env=environment)
            else:
                run(['npm', 'run', 'lint'], work, env=environment)
                environment['VITE_API_URL'] = config['api_url']
            run(['npm', 'run', 'build'], work, env=environment)
        elif kind == 'mobile':
            # Current debug-signed setup must not silently become a production APK.
            gradle = (work / 'android/app/build.gradle.kts').read_text()
            if 'signingConfigs.getByName("debug")' in gradle or 'applicationId = "com.example.setta"' in gradle:
                raise RuntimeError('Defina identidade Android e assinatura release definitiva antes de gerar a versão de produção. A configuração atual usa exemplo/assinatura debug.')
            if not (root / 'android/key.properties').is_file():
                raise RuntimeError('Configure android/key.properties e sua chave de assinatura antes de gerar o APK de produção; veja docs/release.md.')
            for relative in ('android/key.properties',):
                if (root / relative).is_file():
                    shutil.copy2(root / relative, work / relative)
            run(['flutter', 'pub', 'get'], work)
            run(['flutter', 'analyze'], work)
            run(['flutter', 'test'], work)
            run(['flutter', 'build', 'apk', '--release', '-t', 'lib/main_prod.dart'], work)
        elif kind == 'static':
            for required in ('index.html', 'style.css', 'script.js'):
                if not (work / required).is_file():
                    raise RuntimeError('Arquivo do site ausente: ' + required)
        else:
            raise RuntimeError('Tipo de projeto desconhecido.')
        artifact = Path(temporary) / 'artifact'
        artifact.mkdir()
        if kind == 'api':
            shutil.copytree(work / 'dist', artifact / 'dist')
            shutil.copytree(work / 'migrations', artifact / 'migrations')
            for filename in ('package.json', 'package-lock.json'):
                shutil.copy2(work / filename, artifact / filename)
        elif kind == 'portal':
            shutil.copytree(work / 'dist', artifact, dirs_exist_ok=True)
        elif kind == 'mobile':
            shutil.copy2(work / 'build/app/outputs/flutter-apk/app-release.apk', artifact / 'setta-prod.apk')
        else:
            # Publish only web assets: exclude docs, interviews, repo metadata and scripts.
            for filename in ('index.html', 'style.css', 'script.js'):
                shutil.copy2(work / filename, artifact / filename)
            for directory in ('assets', 'images', 'fonts'):
                if (work / directory).is_dir():
                    shutil.copytree(work / directory, artifact / directory)
            if (work / '.htaccess').is_file():
                shutil.copy2(work / '.htaccess', artifact / '.htaccess')
        validate_artifact(kind, artifact)
        metadata = {'project': config['name'], 'commit': commit, 'previous_prod': production,
                    'created_at': timestamp, 'release_id': release_id,
                    'state': 'validated', 'kind': kind}
        (artifact / 'release-version.json').write_text(json.dumps(metadata, indent=2) + '\n')
        if args.publish and kind != 'mobile':
            # This commit marker must also be generated by the remote build command.
            if deploy.get('method') == 'hostinger-git' and deploy.get('commit_verification') is not True:
                raise RuntimeError('Configure a geração de release-version.json na hospedagem e marque commit_verification=true. Um HTTP 200 sozinho não comprova publicação.')
        output = root / '.releases' / release_id
        output.mkdir(parents=True)
        suffix = '.apk' if kind == 'mobile' else '.tar.gz'
        target = output / (config['name'] + '-' + commit[:12] + suffix)
        if kind == 'mobile':
            shutil.copy2(artifact / 'setta-prod.apk', target)
        else:
            with tarfile.open(target, 'w:gz') as tar:
                tar.add(artifact, arcname='.')
        metadata['artifact_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        receipt = output / 'receipt.json'
        receipt.write_text(json.dumps(metadata, indent=2) + '\n')
        print(f"Validação concluída. Artefato: {target}", flush=True)
        if not args.publish:
            print('Nenhuma branch remota alterada.')
            return
        run(['git', 'fetch', '--prune', remote], root)
        if resolve(root, 'refs/remotes/origin/prod') != production or resolve(root, 'refs/remotes/origin/dev') != commit:
            raise RuntimeError('dev/prod mudou durante a validação. Rode novamente para revisar a versão atual; nada foi promovido.')
        # No checkout, merge, reset, force push or local branch mutation.
        # Lease locks the exact observed tip; ancestry above prevents rewriting history.
        lease = '--force-with-lease=refs/heads/prod:' + (production or '')
        run(['git', 'push', lease, remote, commit + ':refs/heads/prod'], root)
        metadata['state'] = 'promoted'
        receipt.write_text(json.dumps(metadata, indent=2) + '\n')
        if kind == 'mobile':
            print('origin/prod atualizada; APK pronto para entrega manual. Nenhuma publicação em loja.')
            return
        if deploy['method'] == 'ssh':
            print('Enviando artefato validado para a hospedagem...', flush=True)
            destination_path = deploy['ssh_alias'] + ':' + shlex.quote(deploy['web_root'].rstrip('/') + '/')
            # No deletion of server files. New assets go first; the version marker goes last.
            run(['rsync', '-rlt', '--delay-updates', '--exclude=release-version.json',
                 '-e', 'ssh -o BatchMode=yes', str(artifact) + '/', destination_path], root)
            run(['rsync', '-t', '-e', 'ssh -o BatchMode=yes', str(artifact / 'release-version.json'), destination_path], root)
        print('origin/prod atualizada. Aguardando a hospedagem publicar o commit...', flush=True)
        timeout = int(deploy.get('timeout_seconds', 300))
        started = time.monotonic()
        last_notice = started
        while time.monotonic() - started < timeout:
            try:
                url = deploy['verification_url'] + ('&' if '?' in deploy['verification_url'] else '?') + 'release=' + commit
                request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(request, timeout=10) as response:
                    actual = json.load(response)
                if actual.get('commit') == commit:
                    metadata['state'] = 'deployed'
                    receipt.write_text(json.dumps(metadata, indent=2) + '\n')
                    print('Publicação confirmada: hospedagem está servindo o commit promovido.')
                    return
            except (OSError, ValueError):
                pass
            if time.monotonic() - last_notice >= 30:
                print('Ainda aguardando o commit na hospedagem...', flush=True)
                last_notice = time.monotonic()
            time.sleep(5)
        raise RuntimeError('prod foi promovida, mas a publicação não foi confirmada no prazo. Confira o deploy no hPanel e receipt.json; não há rollback automático.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print('ERRO: ' + str(error), file=sys.stderr)
        sys.exit(1)
