class Extra < Formula
  include Language::Python::Virtualenv

  desc "Flashless Linux, Windows & macOS Computer-Use Engine & MCP Server"
  homepage "https://extra.yantraos.com"
  url "https://github.com/AIYantra/extra/archive/refs/tags/v0.3.4.tar.gz"
  sha256 "0a94a273624e24b7347d725ac721a411601562ea2201414550514109de978bcc"
  license "MIT"

  depends_on "python@3.12"
  depends_on :macos => :monterey

  def install
    virtualenv_install_with_resources
    bin.install_symlink libexec/"bin/extra" => "extra"
  end

  def post_install
    system bin/"extra", "doctor"
  end

  test do
    assert_match "extra 0.3.4", shell_output("#{bin}/extra --version")
  end
end
