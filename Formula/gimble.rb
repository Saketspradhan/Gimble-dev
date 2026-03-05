class Gimble < Formula
  desc "Gimble CLI"
  homepage "https://github.com/Saketspradhan/Gimble-dev"
  version "0.1.14"
  url "https://github.com/Saketspradhan/Gimble-dev/archive/refs/tags/v0.1.14.tar.gz"
  sha256 "1b6265aa21b00748b2e6ad73a188a9fd3fffcf7395d7cbea6584c374432d47bc"
  license "MIT"

  depends_on "go" => :build
  depends_on "python@3.12"

  def install
    system "go", "build", "-ldflags", "-X main.version=0.1.14", "-o", bin/"gimble", "./cmd/gimble"
    pkgshare.install "python"
  end

  test do
    assert_match "gimble", shell_output("#{bin}/gimble --version")
  end
end
