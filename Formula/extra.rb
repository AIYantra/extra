class Extra < Formula
  include Language::Python::Virtualenv

  desc "Flashless macOS & Windows Computer-Use Engine & MCP Server"
  homepage "https://extra.yantraos.com"
  url "https://github.com/AIYantra/extra/archive/refs/tags/v0.2.1.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
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
    assert_match "extra 0.2.1", shell_output("#{bin}/extra --version")
  end
end
