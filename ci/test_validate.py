import unittest
from validate import check_image, local_path


class ImagePolicyTests(unittest.TestCase):
    def test_approved_digest(self):
        check_image("frontend", "phx.ocir.io/axkouhjvgred/online-store/frontend@sha256:" + "a" * 64)

    def test_bad_references(self):
        for image in [None, "postgres:BUILD_REQUIRED", "nginx:latest",
                      "phx.ocir.io/axkouhjvgred/online-store/backend@sha256:" + "a" * 64,
                      "phx.ocir.io/axkouhjvgred/online-store/frontend@sha256:abc"]:
            with self.subTest(image=image), self.assertRaises(ValueError):
                check_image("frontend", image)

    def test_path_escape(self):
        with self.assertRaises(ValueError):
            local_path("../platform-backend")


if __name__ == "__main__":
    unittest.main()
