"""Entry point for trading-copilot CLI."""

# Enable Python 3.9 support for union syntax (X | None)
try:
    import eval_type_backport
    eval_type_backport.install_patch()
except ImportError:
    pass

from trading_copilot.cli import app

if __name__ == "__main__":
    app()