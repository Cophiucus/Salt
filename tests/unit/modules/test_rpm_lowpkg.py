"""
    :codeauthor: Jayesh Kariya <jayeshk@saltstack.com>
"""


import salt.modules.rpm_lowpkg as rpm
from tests.support.mixins import LoaderModuleMockMixin
from tests.support.mock import MagicMock, patch
from tests.support.unit import TestCase


def _called_with_root(mock):
    cmd = " ".join(mock.call_args[0][0])
    return cmd.startswith("rpm --root /")


class RpmTestCase(TestCase, LoaderModuleMockMixin):
    """
    Test cases for salt.modules.rpm
    """

    def setup_loader_modules(self):
        return {rpm: {"rpm": MagicMock(return_value=MagicMock)}}

    # 'list_pkgs' function tests: 2

    def test_list_pkgs(self):
        """
        Test if it list the packages currently installed in a dict
        """
        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            self.assertDictEqual(rpm.list_pkgs(), {})
            self.assertFalse(_called_with_root(mock))

    def test_list_pkgs_root(self):
        """
        Test if it list the packages currently installed in a dict,
        called with root parameter
        """
        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            rpm.list_pkgs(root="/")
            self.assertTrue(_called_with_root(mock))

    # 'verify' function tests: 2

    def test_verify(self):
        """
        Test if it runs an rpm -Va on a system, and returns the
        results in a dict
        """
        mock = MagicMock(
            return_value={"stdout": "", "stderr": "", "retcode": 0, "pid": 12345}
        )
        with patch.dict(rpm.__salt__, {"cmd.run_all": mock}):
            self.assertDictEqual(rpm.verify("httpd"), {})
            self.assertFalse(_called_with_root(mock))

    def test_verify_root(self):
        """
        Test if it runs an rpm -Va on a system, and returns the
        results in a dict, called with root parameter
        """
        mock = MagicMock(
            return_value={"stdout": "", "stderr": "", "retcode": 0, "pid": 12345}
        )
        with patch.dict(rpm.__salt__, {"cmd.run_all": mock}):
            rpm.verify("httpd", root="/")
            self.assertTrue(_called_with_root(mock))

    # 'file_list' function tests: 2

    def test_file_list(self):
        """
        Test if it list the files that belong to a package.
        """
        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            self.assertDictEqual(rpm.file_list("httpd"), {"errors": [], "files": []})
            self.assertFalse(_called_with_root(mock))

    def test_file_list_root(self):
        """
        Test if it list the files that belong to a package, using the
        root parameter.
        """

        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            rpm.file_list("httpd", root="/")
            self.assertTrue(_called_with_root(mock))

    # 'file_dict' function tests: 2

    def test_file_dict(self):
        """
        Test if it list the files that belong to a package
        """
        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            self.assertDictEqual(rpm.file_dict("httpd"), {"errors": [], "packages": {}})
            self.assertFalse(_called_with_root(mock))

    def test_file_dict_root(self):
        """
        Test if it list the files that belong to a package
        """
        mock = MagicMock(return_value="")
        with patch.dict(rpm.__salt__, {"cmd.run": mock}):
            rpm.file_dict("httpd", root="/")
            self.assertTrue(_called_with_root(mock))

    # 'owner' function tests: 1

    def test_owner(self):
        """
        Test if it return the name of the package that owns the file.
        """
        self.assertEqual(rpm.owner(), "")

        ret = "file /usr/bin/salt-jenkins-build is not owned by any package"
        mock = MagicMock(return_value=ret)
        with patch.dict(rpm.__salt__, {"cmd.run_stdout": mock}):
            self.assertEqual(rpm.owner("/usr/bin/salt-jenkins-build"), "")
            self.assertFalse(_called_with_root(mock))

        ret = {
            "/usr/bin/vim": "vim-enhanced-7.4.160-1.e17.x86_64",
            "/usr/bin/python": "python-2.7.5-16.e17.x86_64",
        }
        mock = MagicMock(
            side_effect=[
                "python-2.7.5-16.e17.x86_64",
                "vim-enhanced-7.4.160-1.e17.x86_64",
            ]
        )
        with patch.dict(rpm.__salt__, {"cmd.run_stdout": mock}):
            self.assertDictEqual(rpm.owner("/usr/bin/python", "/usr/bin/vim"), ret)
            self.assertFalse(_called_with_root(mock))

    def test_owner_root(self):
        """
        Test if it return the name of the package that owns the file,
        using the parameter root.
        """
        self.assertEqual(rpm.owner(), "")

        ret = "file /usr/bin/salt-jenkins-build is not owned by any package"
        mock = MagicMock(return_value=ret)
        with patch.dict(rpm.__salt__, {"cmd.run_stdout": mock}):
            rpm.owner("/usr/bin/salt-jenkins-build", root="/")
            self.assertTrue(_called_with_root(mock))

    # 'checksum' function tests: 2

    def test_checksum(self):
        """
        Test if checksum validate as expected
        """
        ret = {
            "file1.rpm": True,
            "file2.rpm": False,
            "file3.rpm": False,
        }

        mock = MagicMock(side_effect=[True, 0, True, 1, False, 0])
        with patch.dict(rpm.__salt__, {"file.file_exists": mock, "cmd.retcode": mock}):
            self.assertDictEqual(
                rpm.checksum("file1.rpm", "file2.rpm", "file3.rpm"), ret
            )
            self.assertFalse(_called_with_root(mock))

    def test_checksum_root(self):
        """
        Test if checksum validate as expected, using the parameter
        root
        """
        mock = MagicMock(side_effect=[True, 0])
        with patch.dict(rpm.__salt__, {"file.file_exists": mock, "cmd.retcode": mock}):
            rpm.checksum("file1.rpm", root="/")
            self.assertTrue(_called_with_root(mock))

    @patch("salt.modules.rpm_lowpkg.HAS_RPM", True)
    @patch("salt.modules.rpm_lowpkg.rpm.labelCompare", return_value=-1)
    @patch("salt.modules.rpm_lowpkg.log")
    def test_version_cmp_rpm(self, mock_log, mock_labelCompare):
        """
        Test package version if RPM-Python is installed

        :return:
        """
        self.assertEqual(-1, rpm.version_cmp("1", "2"))
        self.assertEqual(mock_log.warning.called, False)
        self.assertEqual(mock_labelCompare.called, True)

    @patch("salt.modules.rpm_lowpkg.HAS_RPM", False)
    @patch("salt.modules.rpm_lowpkg.HAS_RPMUTILS", True)
    @patch("salt.modules.rpm_lowpkg.rpmUtils", create=True)
    @patch("salt.modules.rpm_lowpkg.log")
    def test_version_cmp_rpmutils(self, mock_log, mock_rpmUtils):
        """
        Test package version if rpmUtils.miscutils called

        :return:
        """
        mock_rpmUtils.miscutils = MagicMock()
        mock_rpmUtils.miscutils.compareEVR = MagicMock(return_value=-1)
        self.assertEqual(-1, rpm.version_cmp("1", "2"))
        self.assertEqual(mock_log.warning.called, True)
        self.assertEqual(mock_rpmUtils.miscutils.compareEVR.called, True)
        self.assertEqual(
            mock_log.warning.mock_calls[0][1][0],
            "Please install a package that provides rpm.labelCompare for more accurate"
            " version comparisons.",
        )

    @patch("salt.modules.rpm_lowpkg.HAS_RPM", False)
    @patch("salt.modules.rpm_lowpkg.HAS_RPMUTILS", False)
    @patch("salt.utils.path.which", return_value=True)
    @patch("salt.modules.rpm_lowpkg.log")
    def test_version_cmp_rpmdev_vercmp(self, mock_log, mock_which):
        """
        Test package version if rpmdev-vercmp is installed

        :return:
        """
        mock__salt__ = MagicMock(return_value={"retcode": 12})
        with patch.dict(rpm.__salt__, {"cmd.run_all": mock__salt__}):
            self.assertEqual(-1, rpm.version_cmp("1", "2"))
            self.assertEqual(mock__salt__.called, True)
            self.assertEqual(mock_log.warning.called, True)
            self.assertEqual(
                mock_log.warning.mock_calls[0][1][0],
                "Please install a package that provides rpm.labelCompare for more"
                " accurate version comparisons.",
            )
            self.assertEqual(
                mock_log.warning.mock_calls[1][1][0],
                "Installing the rpmdevtools package may surface dev tools in"
                " production.",
            )

    @patch("salt.modules.rpm_lowpkg.HAS_RPM", False)
    @patch("salt.modules.rpm_lowpkg.HAS_RPMUTILS", False)
    @patch("salt.utils.versions.version_cmp", return_value=-1)
    @patch("salt.utils.path.which", return_value=False)
    @patch("salt.modules.rpm_lowpkg.log")
    def test_version_cmp_python(self, mock_log, mock_which, mock_version_cmp):
        """
        Test package version if falling back to python

        :return:
        """
        self.assertEqual(-1, rpm.version_cmp("1", "2"))
        self.assertEqual(mock_version_cmp.called, True)
        self.assertEqual(mock_log.warning.called, True)
        self.assertEqual(
            mock_log.warning.mock_calls[0][1][0],
            "Please install a package that provides rpm.labelCompare for more accurate"
            " version comparisons.",
        )
        self.assertEqual(
            mock_log.warning.mock_calls[1][1][0],
            "Falling back on salt.utils.versions.version_cmp() for version comparisons",
        )
