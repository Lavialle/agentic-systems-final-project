import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrap_dossiers_legislatifs(driver):
    wait = WebDriverWait(driver, 10)

    url = 'https://www.assemblee-nationale.fr/dyn/17/dossiers'
    driver.get(url)

    all_urls = []
    page_num = 1

    while True:
        print(f"\n========== DOSSIERS LÉGISLATIFS — PAGE {page_num} ==========")

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@class,'button') and contains(@class,'_colored-white')]")
            )
        )

        time.sleep(1)

        buttons = driver.find_elements(
            By.XPATH, "//a[contains(@class,'button') and contains(@class,'_colored-white')]"
        )

        urls = [b.get_attribute("href") for b in buttons]
        textes = [u for u in urls if u and "/dyn/17/textes/" in u]

        print("URLs trouvées sur cette page :")
        for u in textes:
            print("   →", u)

        all_urls.extend(textes)

        print(f"Total cumulé : {len(all_urls)}")

        try:
            next_btn = driver.find_element(
                By.XPATH,
                "//div[contains(@class,'an-pagination--item') and contains(@class,'next')]//a"
            )

            if not next_btn.is_displayed():
                break

            driver.execute_script("arguments[0].click();", next_btn)
            page_num += 1
            time.sleep(5)

        except:
            print("\n>>> Fin du scraping DOSSIER LÉGISLATIF.")
            break

    df = pd.DataFrame({
        "url": list(set(all_urls)),
        "provenance": "dossiers_legislatifs"
    })

    return df
