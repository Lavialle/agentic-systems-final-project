import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrap_projets_lois(driver):
    wait = WebDriverWait(driver, 10)

    url = "https://www2.assemblee-nationale.fr/documents/liste/(type)/projets-loi"
    driver.get(url)

    all_urls = []
    page_num = 1

    while True:
        print(f"\n========== PROJETS DE LOI — PAGE {page_num} ==========")

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        time.sleep(3)

        links = driver.find_elements(
            By.XPATH, "//a[contains(@href, '/dyn/old/17/projets/')]"
        )

        urls = [l.get_attribute("href") for l in links]

        print("URLs trouvées sur cette page :")
        for u in urls:
            print("   →", u)

        print(f"Nombre d'URLs sur cette page : {len(urls)}")

        all_urls.extend(urls)
        print(f"Total cumulé : {len(all_urls)}")

        try:
            next_btn = driver.find_element(By.XPATH, "//li[contains(@class,'next')]/a")
            driver.execute_script("arguments[0].click();", next_btn)
            page_num += 1
            time.sleep(5)

        except Exception:
            print("\n>>> Fin du scraping PROJETS DE LOI.")
            break

    df = pd.DataFrame({
        "url": list(set(all_urls)),  
        "provenance": "projets_lois"
    })

    return df
