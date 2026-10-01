"""Release checks use disposable local repositories, never GitHub/Hostinger."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('release.py')


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.remote = self.base / 'origin.git'
        self.command(['git', 'init', '--bare', str(self.remote)], self.base)
        self.command(['git', 'init', '-b', 'main'], self.repo)
        self.g('config', 'user.email', 'release-test@example.invalid')
        self.g('config', 'user.name', 'Release Test')
        (self.repo / 'scripts').mkdir()
        shutil.copy2(SCRIPT, self.repo / 'scripts/release.py')
        (self.repo / '.gitignore').write_text('.releases/\n.deploy.local.json\n.env\n__pycache__/\n')
        (self.repo / 'release.json').write_text(json.dumps({'name': 'fixture', 'kind': 'static'}))
        for name in ('index.html', 'style.css', 'script.js'):
            (self.repo / name).write_text('fixture')
        (self.repo / 'private-interview.docx').write_text('not a web asset')
        self.g('add', '.')
        self.g('commit', '-m', 'baseline')
        self.g('remote', 'add', 'origin', str(self.remote))
        self.g('push', '-u', 'origin', 'main')
        self.g('checkout', '-b', 'dev')
        (self.repo / 'index.html').write_text('new version')
        self.g('add', '.')
        self.g('commit', '-m', 'new version')
        self.g('push', '-u', 'origin', 'dev')
        self.sha = self.g('rev-parse', 'HEAD')
        spec = importlib.util.spec_from_file_location('release_fixture', self.repo / 'scripts/release.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def command(self, args, cwd):
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()

    def g(self, *args):
        return self.command(['git', *args], self.repo)

    def invoke(self, *args):
        with patch.object(sys, 'argv', ['release.py', *args]), contextlib.redirect_stdout(io.StringIO()):
            self.module.main()

    def deployment(self):
        (self.repo / '.deploy.local.json').write_text(json.dumps({
            'method': 'hostinger-git', 'branch': 'prod', 'auto_deploy_confirmed': True,
            'commit_verification': True, 'verification_url': 'https://fixture.invalid/release-version.json',
            'timeout_seconds': 1,
        }))

    def served(self):
        return io.StringIO(json.dumps({'commit': self.sha}))

    def test_plan_leaves_worktree_and_remote_unchanged(self):
        (self.repo / 'style.css').write_text('uncommitted')
        before = self.g('status', '--porcelain')
        self.invoke('--plan')
        self.assertEqual(before, self.g('status', '--porcelain'))
        self.assertEqual('', self.g('ls-remote', 'origin', 'refs/heads/prod'))

    def test_check_builds_exact_commit_and_excludes_private_files(self):
        (self.repo / '.env').write_text('SECRET=fixture-secret')
        self.invoke('--check')
        archive = next((self.repo / '.releases').glob('*/*.tar.gz'))
        with tarfile.open(archive) as tar:
            names = tar.getnames()
            self.assertNotIn('./private-interview.docx', names)
            self.assertNotIn('./.env', names)
            self.assertNotIn('./scripts', names)
            self.assertEqual(b'new version', tar.extractfile('./index.html').read())
        self.assertEqual('', self.g('ls-remote', 'origin', 'refs/heads/prod'))

    def test_dirty_worktree_blocks_publish(self):
        (self.repo / 'style.css').write_text('uncommitted')
        with self.assertRaisesRegex(RuntimeError, 'sem commit'):
            self.invoke('--publish')

    def test_unpushed_dev_blocks_check(self):
        (self.repo / 'style.css').write_text('local commit')
        self.g('add', '.')
        self.g('commit', '-m', 'not pushed')
        with self.assertRaisesRegex(RuntimeError, 'difere'):
            self.invoke('--check')

    def test_divergent_prod_is_not_overwritten(self):
        self.g('checkout', 'main')
        (self.repo / 'style.css').write_text('production hotfix')
        self.g('add', '.')
        self.g('commit', '-m', 'hotfix')
        self.g('push', 'origin', 'HEAD:prod')
        self.g('checkout', 'dev')
        with self.assertRaisesRegex(RuntimeError, 'divergiram'):
            self.invoke('--publish')

    def test_missing_destination_blocks_publish(self):
        with self.assertRaisesRegex(RuntimeError, 'Falta .deploy.local.json'):
            self.invoke('--publish')
        self.assertEqual('', self.g('ls-remote', 'origin', 'refs/heads/prod'))

    def test_publish_promotes_and_confirms_exact_commit(self):
        self.deployment()
        with patch.object(self.module.urllib.request, 'urlopen', side_effect=lambda *a, **kw: self.served()):
            self.invoke('--publish')
        self.assertTrue(self.g('ls-remote', 'origin', 'refs/heads/prod').startswith(self.sha))
        self.assertEqual('dev', self.g('branch', '--show-current'))
        receipt = json.loads(next((self.repo / '.releases').glob('*/receipt.json')).read_text())
        self.assertEqual('deployed', receipt['state'])
        self.assertEqual(self.sha, receipt['commit'])

    def test_lease_blocks_concurrent_creation_after_final_fetch(self):
        self.deployment()
        original = self.module.run
        main = self.g('rev-parse', 'main')
        def racing_run(args, *rest, **kwargs):
            if args[:2] == ['git', 'push']:
                self.g('push', 'origin', main + ':refs/heads/prod')
            return original(args, *rest, **kwargs)
        with patch.object(self.module, 'run', side_effect=racing_run):
            with self.assertRaises(RuntimeError):
                self.invoke('--publish')
        self.assertTrue(self.g('ls-remote', 'origin', 'refs/heads/prod').startswith(main))

    def test_old_commit_does_not_count_as_deployed(self):
        self.deployment()
        with patch.object(self.module.urllib.request, 'urlopen', side_effect=lambda *a, **kw: io.StringIO('{"commit":"old"}')):
            with patch.object(self.module.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'não foi confirmada'):
                    self.invoke('--publish')
        receipt = json.loads(next((self.repo / '.releases').glob('*/receipt.json')).read_text())
        self.assertEqual('promoted', receipt['state'])

    def test_database_changes_require_explicit_readiness(self):
        (self.repo / 'release.json').write_text(json.dumps({'name': 'fixture', 'kind': 'api'}))
        (self.repo / 'migrations').mkdir()
        (self.repo / 'migrations/new.sql').write_text('test-only')
        self.g('add', '.')
        self.g('commit', '-m', 'schema')
        self.g('push', 'origin', 'dev')
        with self.assertRaisesRegex(RuntimeError, 'database-ready'):
            self.invoke('--publish')

    def test_deleted_remote_prod_is_pruned_before_validation(self):
        self.g('push', 'origin', 'main:prod')
        self.g('fetch', 'origin')
        self.g('push', 'origin', ':prod')
        self.invoke('--check')
        self.assertIsNone(self.module.resolve(self.repo, 'refs/remotes/origin/prod'))

    def test_mobile_requires_private_signing_configuration(self):
        (self.repo / 'release.json').write_text(json.dumps({'name': 'fixture', 'kind': 'mobile'}))
        (self.repo / 'android/app').mkdir(parents=True)
        (self.repo / 'android/app/build.gradle.kts').write_text('applicationId = "br.com.varten.setta"')
        self.g('add', '.')
        self.g('commit', '-m', 'mobile')
        self.g('push', 'origin', 'dev')
        with self.assertRaisesRegex(RuntimeError, 'key.properties'):
            self.invoke('--check')


if __name__ == '__main__':
    unittest.main()
