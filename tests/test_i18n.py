"""Unit tests for simulator/i18n.py localization."""
from simulator.i18n import t, TRANSLATIONS


def test_i18n_translation_keys_exist():
    assert "app_title" in TRANSLATIONS
    assert "decision_title" in TRANSLATIONS
    assert "loan_amount" in TRANSLATIONS


def test_i18n_translation_languages():
    en_title = t("app_title", lang="en")
    fr_title = t("app_title", lang="fr")
    assert en_title == "Dump Truck Finance & Leasing Simulator"
    assert fr_title == "Simulateur Financier de Flotte de Bennes & Crédit-Bail"


def test_i18n_missing_key_fallback():
    res = t("non_existent_key_sample", lang="fr")
    assert res == "Non Existent Key Sample"

