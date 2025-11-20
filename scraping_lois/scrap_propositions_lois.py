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

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        time.sleep(1)

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

        old_links = links

        try:
            next_btn = driver.find_element(
                By.XPATH,
                "//a[contains(@class,'ajax-listes')]//span[contains(.,'Suivant') or contains(.,'Next')]/.."
            )

            print("→ Clic sur 'Suivant »'")
            driver.execute_script("arguments[0].click();", next_btn)

            if old_links:
                wait.until(EC.staleness_of(old_links[0]))

            time.sleep(5)
            page_num += 1

        except Exception:
            print("\n>>> Plus de bouton 'Suivant'. Fin du scraping.")
            break

    df = pd.DataFrame({
        "url": list(set(all_urls)),  
        "provenance": "propositions_lois"
    })

    return df
