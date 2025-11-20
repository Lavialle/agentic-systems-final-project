import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import pandas as pd
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from scrap_projets_lois import scrap_projets_lois
from scrap_propositions_lois import scrap_propositions_lois
from scrap_rapports_legislatifs import scrap_rapports_legislatifs
from scrap_textes_adoptes import scrap_textes_adoptes
from scrap_dossiers_legislatifs import scrap_dossiers_legislatifs


def make_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--headless")
    return webdriver.Chrome(options=options)


def scrap_urls_all():
    print("\n===== SCRAP PROJETS DE LOI =====")
    driver = make_driver()
    df_projets = scrap_projets_lois(driver)
    driver.quit()

    print("\n===== SCRAP PROPOSITIONS DE LOI =====")
    driver = make_driver()
    df_propositions = scrap_propositions_lois(driver)
    driver.quit()

    print("\n===== SCRAP RAPPORTS =====")
    driver = make_driver()
    df_rapports = scrap_rapports_legislatifs(driver)
    driver.quit()

    print("\n===== SCRAP TEXTES ADOPTÉS =====")
    driver = make_driver()
    df_ta = scrap_textes_adoptes(driver)
    driver.quit()

    print("\n===== SCRAP DOSSIERS LÉGISLATIFS =====")
    driver = make_driver()
    df_dossiers = scrap_dossiers_legislatifs(driver)
    driver.quit()

    df_final = pd.concat([
        df_projets,
        df_propositions,
        df_rapports,
        df_ta,
        df_dossiers
    ], ignore_index=True)

    return df_final
