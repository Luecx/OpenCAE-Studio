"""Canonical dropdown/select control for forms and inspectors."""

# ChoiceInput contains the established painted-chevron and full-height popup
# behavior.  Re-exporting the class under the structural name keeps one
# implementation while new code uses the category-oriented API.
from opencae.ui.primitives.inputs.choice_input import ChoiceInput

SelectForm = ChoiceInput

__all__ = ["SelectForm"]
