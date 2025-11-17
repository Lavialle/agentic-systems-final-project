import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrap_propositions_lois(driver):
    wait = WebDriverWait(driver, 10)

    url = "https://www2.assemblee-nationale.fr/documents/liste/(type)/propositions-loi"
    driver.get(url)

    all_urls = []
    page_num = 1

    while True:
        print(f"\n========== PROPOSITIONS DE LOI — PAGE {page_num} ==========")

        # Attendre qu'il y ait des liens
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        time.sleep(1)

        # Récupérer uniquement les liens DLR (ancien format ASP)
        links = driver.find_elements(
            By.XPATH, "//a[contains(@href, '/dyn/old/17/propositions')]"
        )

        urls = [l.get_attribute("href") for l in links]

        print("URLs trouvées sur cette page :")
        for u in urls:
            print("   →", u)

        print(f"Nombre d'URLs sur cette page : {len(urls)}")

        all_urls.extend(urls)
        print(f"TOTAL cumulé : {len(all_urls)}")

        # Garder un référence pour détecter la mise à jour AJAX
        old_links = links

        # Bouton Suivant AJAX
        try:
            next_btn = driver.find_element(
                By.XPATH,
                "//a[contains(@class,'ajax-listes')]//span[contains(.,'Suivant')]/.."
            )

            print("→ Clic sur 'Suivant »'")
            driver.execute_script("arguments[0].click();", next_btn)

            # Attendre que l'ancienne liste disparaisse
            if old_links:
                wait.until(EC.staleness_of(old_links[0]))

            time.sleep(1.2)
            page_num += 1

        except Exception:
            print("\n>>> Plus de bouton 'Suivant'. Fin du scraping.")
            break

    # Construire DataFrame
    df = pd.DataFrame({
        "url": list(set(all_urls)),  # dédoublonnage
        "provenance": "propositions_lois"
    })

    return df
