class Gimble < Formula
  desc "Gimble CLI"
  homepage "https://github.com/Saketspradhan/Gimble-dev"
  version "0.1.9"
  url "https://github.com/Saketspradhan/Gimble-dev/archive/refs/tags/v0.1.9.tar.gz"
  sha256 "866cfdc06e2d83d61201a240094bcc8d251e1227755a8b34ec75d8f05083c65c"
  license "MIT"

  depends_on "go" => :build
  depends_on "python@3.12"

  def install
    system "go", "build", "-ldflags", "-X main.version=0.1.9", "-o", bin/"gimble", "./cmd/gimble"
    pkgshare.install "python"
  end

  test do
    assert_match "gimble", shell_output("#{bin}/gimble --version")
  end
end
