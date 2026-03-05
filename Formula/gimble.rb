class Gimble < Formula
  desc "Gimble CLI"
  homepage "https://github.com/Saketspradhan/Gimble-dev"
  version "0.1.13"
  url "https://github.com/Saketspradhan/Gimble-dev/archive/refs/tags/v0.1.13.tar.gz"
  sha256 "6b8356a71a637d17321a86c64f58f44035fe66fcb709b02d63ec9c839925e7db"
  license "MIT"

  depends_on "go" => :build
  depends_on "python@3.12"

  def install
    system "go", "build", "-ldflags", "-X main.version=0.1.13", "-o", bin/"gimble", "./cmd/gimble"
    pkgshare.install "python"
  end

  test do
    assert_match "gimble", shell_output("#{bin}/gimble --version")
  end
end
