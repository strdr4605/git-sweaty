import os
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WRAPPER_PATH = os.path.join(ROOT_DIR, "scripts", "bootstrap.ps1")
README_PATH = os.path.join(ROOT_DIR, "README.md")


class BootstrapWindowsWrapperTests(unittest.TestCase):
    def _read_wrapper(self) -> str:
        with open(WRAPPER_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def test_windows_wrapper_runs_native_online_only_setup(self) -> None:
        wrapper = self._read_wrapper()

        self.assertIn("Preparing native Windows setup (online-only, no WSL required)...", wrapper)
        self.assertIn("winget", wrapper)
        self.assertIn("GitHub.cli", wrapper)
        self.assertIn("Python.Python.3.13", wrapper)
        self.assertIn("auth login --web --git-protocol https --scopes repo,workflow", wrapper)
        self.assertIn("repo fork", wrapper)
        self.assertIn("Invoke-WebRequest", wrapper)
        self.assertIn("Expand-Archive", wrapper)
        self.assertIn("scripts\\setup_auth.py", wrapper)
        self.assertNotIn("wsl.exe", wrapper)

    def test_windows_wrapper_declares_param_block_before_executable_statements(self) -> None:
        with open(WRAPPER_PATH, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        first_code_line = next(line for line in lines if line.strip())
        self.assertEqual(first_code_line, "param(")

    def test_windows_wrapper_uses_zip_download_and_not_unix_bootstrap(self) -> None:
        wrapper = self._read_wrapper()

        self.assertIn("archive/refs/heads/$defaultBranch.zip", wrapper)
        self.assertIn("Invoke-WebRequest", wrapper)
        self.assertIn("Expand-Archive", wrapper)
        self.assertNotIn("bootstrap.sh", wrapper)
        self.assertNotIn("bash <(", wrapper)
        self.assertNotIn("tar -xzf", wrapper)

    def test_windows_wrapper_installs_python_and_gh_with_user_scope_first(self) -> None:
        wrapper = self._read_wrapper()

        self.assertIn('foreach ($scope in @("user", $null))', wrapper)
        self.assertIn('Invoke-WingetInstall "GitHub.cli" "GitHub CLI"', wrapper)
        self.assertIn('foreach ($packageId in @("Python.Python.3.13", "Python.Python.3.12"))', wrapper)
        self.assertIn('--accept-package-agreements', wrapper)
        self.assertIn('--accept-source-agreements', wrapper)
        self.assertIn('--silent', wrapper)

    def test_windows_wrapper_prefers_existing_fork_then_creates_one(self) -> None:
        wrapper = self._read_wrapper()

        self.assertIn('Invoke-GhJson $GhPath @("repo", "list", $Login, "--fork", "--limit", "1000", "--json", "nameWithOwner,parent")', wrapper)
        self.assertIn('Write-Info "Using existing fork: $existingFork"', wrapper)
        self.assertIn('& $GhPath repo fork $UpstreamRepo --clone=false --remote=false', wrapper)
        self.assertIn('Fail "Unable to create or locate a fork for $UpstreamRepo under $login."', wrapper)

    def test_windows_wrapper_preserves_explicit_repo_and_other_setup_args(self) -> None:
        wrapper = self._read_wrapper()

        self.assertIn('Get-SetupArgValue -Args $Args -Name "--repo"', wrapper)
        self.assertIn('if ([string]::IsNullOrWhiteSpace((Get-SetupArgValue -Args $Args -Name "--repo")))', wrapper)
        self.assertIn('$pythonArgs += @("--repo", $TargetRepo)', wrapper)
        self.assertIn('$pythonArgs += $Args', wrapper)

    def test_windows_wrapper_executes_native_flow_in_expected_order(self) -> None:
        wrapper = self._read_wrapper()

        python_index = wrapper.index("$pythonRuntime = Ensure-PythonRuntime")
        gh_index = wrapper.index("$ghPath = Ensure-GhPath")
        auth_index = wrapper.index("Ensure-GhAuthenticated $ghPath")
        target_index = wrapper.index("$targetRepo = Resolve-TargetRepository")
        launch_index = wrapper.index("$status = Invoke-OnlineSetup")

        self.assertLess(python_index, gh_index)
        self.assertLess(gh_index, auth_index)
        self.assertLess(auth_index, target_index)
        self.assertLess(target_index, launch_index)

    def test_readme_points_windows_quick_start_to_powershell_wrapper(self) -> None:
        with open(README_PATH, "r", encoding="utf-8") as f:
            readme = f.read()

        self.assertIn("scripts/bootstrap.ps1", readme)
        self.assertIn("does not require WSL", readme)
        self.assertIn("install them automatically with `winget`", readme)
        self.assertIn("same terminal session", readme)


if __name__ == "__main__":
    unittest.main()
