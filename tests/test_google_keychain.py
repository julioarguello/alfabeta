import base64
import subprocess

from alfabeta.google.keychain import SERVICE, KeychainStore

SECRET = "1//refresco-inventado_ABC-123"


class Recorder:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.calls: list[tuple[list[str], str | None]] = []
        self.stdout = stdout
        self.returncode = returncode

    def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        self.calls.append((argv, stdin))
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, "")


def test_set_sends_the_secret_on_stdin_never_in_argv():
    rec = Recorder()
    KeychainStore(rec).set("s9/student", SECRET)
    argv, stdin = rec.calls[0]
    assert argv == ["security", "-i"]
    encoded = base64.urlsafe_b64encode(SECRET.encode()).decode()
    assert stdin is not None and encoded in stdin and f"-s {SERVICE} -a s9/student" in stdin
    assert all(SECRET not in a and encoded not in a for a in argv)


def test_get_decodes_what_set_stored():
    encoded = base64.urlsafe_b64encode(SECRET.encode()).decode()
    rec = Recorder(stdout=encoded + "\n")
    assert KeychainStore(rec).get("s9/student") == SECRET
    assert rec.calls[0][0] == ["security", "find-generic-password", "-s", SERVICE, "-a", "s9/student", "-w"]


def test_get_absent_is_none():
    assert KeychainStore(Recorder(returncode=44)).get("s9/student") is None


def test_delete_absent_is_fine():
    KeychainStore(Recorder(returncode=44)).delete("s9/student")
