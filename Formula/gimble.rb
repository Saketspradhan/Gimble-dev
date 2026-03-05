class Gimble < Formula
  desc "Gimble CLI"
  homepage "https://github.com/Saketspradhan/Gimble-dev"
  version "0.1.14"
  url "https://github.com/Saketspradhan/Gimble-dev/archive/refs/tags/v0.1.14.tar.gz"
  sha256 "abf4f9f866cd6c08555913a6945011dc524a12a2e53aa24498f25dd9747a64dd"
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
