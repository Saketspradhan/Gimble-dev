class Gimble < Formula
  desc "Gimble CLI"
  homepage "https://github.com/Saketspradhan/Gimble-dev"
  version "0.1.21"
  url "https://github.com/Saketspradhan/Gimble-dev/archive/refs/tags/v0.1.21.tar.gz"
  sha256 "5e0d93a362eb587e4a5d8a646b01676f4fdaa070b597f25168fdacbea3512a8f"
  license "MIT"

  depends_on "go" => :build
  depends_on "python@3.12"

  def install
    system "go", "build", "-ldflags", "-X main.version=0.1.21", "-o", bin/"gimble", "./cmd/gimble"
    pkgshare.install "python"
  end

  test do
    assert_match "gimble", shell_output("#{bin}/gimble --version")
  end
end
