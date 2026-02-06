"""
HTML report generation for ops-translate.

Provides static, shareable HTML reports that help customers review and understand
translation results before applying them.
"""

from ops_translate.report.html import generate_html_report

__all__ = ["generate_html_report"]
