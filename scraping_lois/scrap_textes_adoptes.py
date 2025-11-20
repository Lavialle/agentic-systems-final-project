import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrap_textes_adoptes(driver):
    wait = WebDriverWait(driver, 10)

    url = "https://www2.assemblee-nationale.fr/documents/liste/(type)/ta"
    driver.get(url)

    all_urls = []
    page_num = 1

    try:
        next_btn = driver.find_element(By.XPATH, "//a[contains(@class,'ajax-listes')]")
        last_offset = next_btn.get_attribute("href")
    except:
        last_offset = None

    while True:
        print(f"\n========== TEXTES ADOPTÉS — PAGE {page_num} ==========")

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        time.sleep(5)

        links = driver.find_elements(
            By.XPATH, "//a[contains(@href, '/dyn/old/17/ta/')]"
        )

        urls = [l.get_attribute("href") for l in links]
        urls = list(dict.fromkeys(urls))  

        print("URLs trouvées :")
        for u in urls:
            print("   →", u)

        print(f"Nombre sur cette page : {len(urls)}")

        all_urls.extend(urls)
        all_urls = list(dict.fromkeys(all_urls))

        print(f"TOTAL cumulé : {len(all_urls)}")

        try:
            next_btn = driver.find_element(
                By.XPATH,
                "//a[contains(@class,'ajax-listes')]//span[contains(.,'Suivant') or contains(.,'Next')]/.."
            )
        except:
            print("\n>>> Fin : bouton 'Suivant' introuvable.")
            break

        next_href = next_btn.get_attribute("href")

        if next_href == last_offset:
            print("\n>>> Offset identique. Fin.")
            break

        print("→ Clic sur Suivant")
        driver.execute_script("arguments[0].click();", next_btn)

        last_offset = next_href
        page_num += 1

        time.sleep(5)

    df = pd.DataFrame({
        "url": all_urls,
        "provenance": "textes_adoptes"
    })

    return df
