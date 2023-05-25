# YÖKSİS Akademik Scraper - Oğuzhan Arı 16.05.2023 10:12
# -----------------------
# Bu modül, YÖKSİS'ten akademik bilgileri çekmek için yazılmıştır.
# Modül Command Line üzerinden kullanılabilir şekilde kurgulanacaktır.
# Temel Akış Şeması:
# 1. Kullanıcıdan hangi anahtar kelime üzerinden arama yapmak istediği bilgisi alınır.
# 2. Kullanıcıdan alınan anahtar kelime sonucunda elde edilen akademisyen sayısı kullanıcıya gösterilir.
# 3. Doğrulama sonrasında program çalışmaya başlar.
# 3.1. Öncelikle bütün sayfa bilgilerini alır ve .csv dosyasında saklanır.
# 3.2. Her sayfa bulunan akademisyenlere ait temel bilgiler alınır. (isim, ünvan, kurum, bölüm, eposta, authorID)
# 3.3. Elde edilen veriler ile kullanıcı profillerinden bilgiler çekilir.
# 3.3.1. Kullanıcı profilinden Kişisel Bilgiler, Kitaplar, Makaleler, Bildiriler ve Projeler kısmında bulunan bilgiler
# çekilir.
# Bütün döngü tamamlandığında hazırlanmış dosyalar kullanıcıya gösterilir.
# Bütün süreç boyunca log tutulur.

# Proje Yapısı Şeması:
# yoksis_akademik/
# ├─ akademik_scraper.py
# ├─ search_result/
# │  ├─ researcher_article_info.csv
# │  ├─ researcher_book_info.csv
# │  ├─ researcher_conference_info.csv
# │  ├─ researcher_education_info.csv
# │  ├─ researcher_info.csv
# │  ├─ researcher_work_info.csv
# │  ├─ config/
# │  │  ├─ application.log
# │  │  ├─ researcher_info.csv

import os
import time
import re
import logging
import random

import pandas as pd
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))


def go_sleep(sleep=random.randint(2, 4)):
    time.sleep(sleep)


def setup_logger(log_file_path):
    logging.basicConfig(filename=log_file_path, level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        encoding='utf-8-sig')


def folder_creation_(search_keyword):
    # Ana klasörün adı
    main_folder_path = "./" + search_keyword

    # Config klasörünün tam yolu
    config_folder_path = main_folder_path + "/config"

    # Log dosyasının tam yolu
    log_file_path = config_folder_path + "/application.log"

    # Ana klasörün var olup olmadığını kontrol et
    if not os.path.exists(main_folder_path):
        os.mkdir(main_folder_path)

    # Config klasörünün var olup olmadığını kontrol et
    if not os.path.exists(config_folder_path):
        os.mkdir(config_folder_path)

    # Logger'ı ayarlayın
    setup_logger(log_file_path)

    # Örnek bir log mesajı yazın
    logging.info(f"'{search_keyword}' ve '{search_keyword}/config' klasörleri oluşturuldu.")
    return main_folder_path, config_folder_path


def search_academic_by_keyword_(keyword):
    logging.info("Driver başlatıldı.")
    driver.get("https://akademik.yok.gov.tr/AkademikArama/")
    go_sleep()

    search_box = driver.find_element(By.ID, "aramaTerim")
    go_sleep()
    logging.info("Arama kutusu bulundu.")
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)
    sonuc = driver.find_element(By.CSS_SELECTOR,
                                "body > div > div:nth-child(9) > div > div > div.bs-example "
                                "> div > div:nth-child(1) > div > div > h3").text
    sonuc = sonuc.split("\n")[1]
    logging.info("Arama sonucu: " + sonuc)
    go_sleep()
    search_url = driver.find_element(By.CSS_SELECTOR,
                                     "body > div > div:nth-child(9) > div > div > div.bs-example "
                                     "> div > div:nth-child(1) > div > div > h3 > a").get_attribute("href")
    return search_url


def search_page_(page_url, config_folder_path):
    web_link = "https://akademik.yok.gov.tr"
    while True:
        # Sayfayı yükle
        driver.get(page_url)
        # get_researcher_info_(page_url, config_folder_path)
        # Sayfanın tamamen yüklenmesini bekleyin
        time.sleep(2)
        # Sayfa kaynağını alın
        page_source = driver.page_source

        # BeautifulSoup nesnesi oluşturun
        soup = BeautifulSoup(page_source, 'lxml')

        pagination = soup.find('ul', {'class': 'pagination'})
        page_links = pagination.find_all('li')
        next_page_link = None
        for page_link in page_links:
            if page_link.text == "»":
                logging.info("» içeren sayfa geçildi.")
                next_page_link = page_link.find('a').get('href')
                page_url = web_link + next_page_link
                break

            if page_link.text == "«":
                logging.info("« içeren sayfa geçildi.")
                continue

            for_page_link = web_link + page_link.find('a').get('href')
            driver.get(for_page_link)
            get_researcher_info_(driver.page_source, config_folder_path)
            go_sleep()
            logging.info(f"{page_link.text}. sayfa tamamlandı.")

        # Eğer sonraki sayfa linki bulunamazsa döngüyü durdur
        if next_page_link is None:
            logging.info("Sonraki sayfa linki bulunamadı. Scraping tamamlandı.")
            break


def get_researcher_info_(page_source, config_folder_path):
    go_sleep()

    author_id = []
    posta = []
    guid = []

    soup = BeautifulSoup(page_source, 'lxml')

    table = soup.find("table", {"class": "table table-striped", "id": "authorlistTb"})
    tbody = table.find('tbody')

    for row in tbody.find_all('tr'):
        tds = row.find_all('td')
        author_id.append(tds[0].text)
        posta.append(tds[3].text)
        guid.append(tds[4].text)

    df = pd.DataFrame({'author_id': author_id,
                       'posta': posta,
                       'guid': guid})
    research_csv_path = os.path.join(config_folder_path, "researcher_info.csv")
    if not os.path.exists(research_csv_path):
        df.to_csv(research_csv_path, index=False)
        logging.info(f"{research_csv_path} oluşturuldu.")
    else:
        df.to_csv(research_csv_path, index=False, mode='a', header=False)
        logging.info(f"{research_csv_path} güncellendi.")


def scrape_profiles_(main_folder_path, config_folder_path):
    profiles = pd.read_csv(config_folder_path + "/researcher_info.csv")
    profiles = profiles['guid'].tolist()

    for index, profil in enumerate(profiles):
        print(f"{index + 1}. profil için scraping başladı. (Kalan profil sayısı: {len(profiles) - index - 1})")
        logging.info(f"{profil}'e ait adrese gidiliyor.")
        scrape_profile_researcher_info_(profil, main_folder_path)
        logging.info(f"{profil}'e ait kişisel bilgiler, çalışma ve eğitim bilgileri alındı.")

        researcher_book_info_(profil, main_folder_path)
        logging.info(f"{profil}'e ait kitap bilgileri alındı.")

        researcher_article_info_(profil, main_folder_path)
        logging.info(f"{profil}'e ait makale bilgileri alındı.")

        researcher_conference_info_(profil, main_folder_path)
        logging.info(f"{profil}'e ait konferans bilgileri alındı.")

    logging.info("Tüm profiller için scraping tamamlandı.")


def scrape_profile_researcher_info_(guid, main_folder_path):
    profile_url = "https://akademik.yok.gov.tr/AkademikArama/AkademisyenGorevOgrenimBilgileri?islem=direct&authorId="
    driver.get(profile_url + guid)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if 'The requested URL was rejected. Please consult with your administrator.' in soup.find('body'):
        logging.error(f"{guid} için kişisel bilgiler sayfasına erişim reddedildi.")
        go_sleep()
        return

    go_sleep()

    profile_researcher_info_(driver.page_source, guid, main_folder_path)
    profile_researcher_academic_info_(driver.page_source, guid, main_folder_path)
    profile_researcher_education_info_(driver.page_source, guid, main_folder_path)


def profile_researcher_info_(page_source, guid, main_folder_path):
    # Sayfa kaynağını alın
    soup = BeautifulSoup(page_source, 'lxml')

    # 'table' etiketini ve 'id' öznitelik değerinin 'authorInfo_' ile başladığı öğeleri bul
    table = soup.find('table', {'id': 'authorlistTb'})
    tds = table.find('tr', {'id': lambda x: x and x.startswith('authorInfo_')})

    # tablonun içindeki ikinci 'td' etiketini bul
    td = tds.find_all('td')[1]  # Python'da indeksleme 0'dan başladığı için, ikinci 'td'
    # etiketi '1' indeksine sahip olacak

    texts = []
    for child in td.children:
        if isinstance(child, NavigableString):
            texts.append(str(child).strip())
        else:
            texts.append(child.text)
    texts = [item for item in texts if item.strip()]
    unvan = texts[0]
    isim = texts[1]
    kadro = texts[2]
    if texts[-1].endswith('.tr') or texts[-1].endswith('.com'):
        anahtar_kelimeler = texts[-2]
        mail = texts[-1]
    else:
        anahtar_kelimeler = texts[-1]
        mail = "Mail Bilgisi Yok"
    # Bütün bunları main_folder_path içindeki 'researcher_info.csv' dosyasına kaydedin
    # Önce dosyanın olup olmadığı kontrol edilsin, yoksa dosya oluşturulsun
    # varsa dosyaya ekleme yapılsın
    researcher_info_csv_path = os.path.join(main_folder_path, "researcher_info.csv")
    if not os.path.exists(researcher_info_csv_path):
        df = pd.DataFrame({'guid': [guid],
                           'unvan': [unvan],
                           'isim': [isim],
                           'kadro': [kadro],
                           'anahtar_kelimeler': [anahtar_kelimeler],
                           'mail': [mail]})
        df.to_csv(researcher_info_csv_path, index=False)
        logging.info(f"{researcher_info_csv_path} oluşturuldu.")
    else:
        df = pd.DataFrame({'guid': [guid],
                           'unvan': [unvan],
                           'isim': [isim],
                           'kadro': [kadro],
                           'anahtar_kelimeler': [anahtar_kelimeler],
                           'mail': [mail]})
        df.to_csv(researcher_info_csv_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_info_csv_path} güncellendi.")


def profile_researcher_academic_info_(page_source, guid, main_folder_path):

    soup = BeautifulSoup(page_source, 'html.parser')
    specific_span = soup.find('span', text='Akademik Görevler')

    # Find the parent 'li' element of this span
    parent_li = specific_span.find_parent('li')
    # Find the 'ul' timeline which is the parent of this 'li'
    timeline = parent_li.find_parent('ul')

    guid_list = []
    academic_year = []
    academic_role = []
    academic_work = []

    # 'li' etiketlerini bul
    for li in timeline.find_all('li'):
        # 'time-label' classına sahip 'li' etiketini kontrol et
        if 'time-label' in li.get('class', []):
            year = li.span.text.strip()  # yılı al
            academic_year.append(year)

        # timeline-footer ve timeline-item classına sahip div'leri kontrol et
        elif li.find('div', {'class': 'timeline-footer'}) and li.find('div', {'class': 'timeline-item'}):
            title = li.find('div', {'class': 'timeline-footer'}).text.strip()  # unvanı al
            workplace = li.find('div', {'class': 'timeline-item'}).text.strip()  # çalışma yerini al
            guid_list.append(guid)
            academic_role.append(title)
            academic_work.append(workplace)

    dataframe = pd.DataFrame({'guid': guid_list,
                              'academic_year': academic_year[1:],
                              'academic_role': academic_role,
                              'academic_work': academic_work})

    researcher_work_info_path = os.path.join(main_folder_path, "researcher_work_info.csv")
    if not os.path.exists(researcher_work_info_path):
        dataframe.to_csv(researcher_work_info_path, index=False)
        logging.info(f"{researcher_work_info_path} oluşturuldu.")
    else:
        dataframe.to_csv(researcher_work_info_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_work_info_path} güncellendi.")


def profile_researcher_education_info_(page_source, guid, main_folder_path):

    soup = BeautifulSoup(page_source, 'html.parser')

    specific_span = soup.find('span', text='Öğrenim Bilgisi')

    # Find the parent 'li' element of this span
    parent_li = specific_span.find_parent('li')
    # Find the 'ul' timeline which is the parent of this 'li'
    timeline = parent_li.find_parent('ul')

    guid_list = []
    education_year = []
    education_type = []
    education_place = []

    # 'li' etiketlerini bul
    for li in timeline.find_all('li'):
        # 'time-label' classına sahip 'li' etiketini kontrol et
        if 'time-label' in li.get('class', []):
            year = li.span.text.strip()  # yılı al
            education_year.append(year)

        # timeline-footer ve timeline-item classına sahip div'leri kontrol et
        elif li.find('div', {'class': 'timeline-footer'}) and li.find('div', {'class': 'timeline-item'}):
            title = li.find('div', {'class': 'timeline-footer'}).text.strip()  # unvanı al
            workplace = li.find('div', {'class': 'timeline-item'}).text.strip()  # çalışma yerini al
            guid_list.append(guid)
            education_type.append(title)
            education_place.append(workplace)

    dataframe = pd.DataFrame({'guid': guid_list,
                              'academic_year': education_year[1:],
                              'academic_role': education_type,
                              'academic_work': education_place})

    researcher_education_info_path = os.path.join(main_folder_path, "researcher_education_info.csv")
    if not os.path.exists(researcher_education_info_path):
        dataframe.to_csv(researcher_education_info_path, index=False)
        logging.info(f"{researcher_education_info_path} oluşturuldu.")
    else:
        dataframe.to_csv(researcher_education_info_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_education_info_path} güncellendi.")


def researcher_book_info_(guid, main_folder_path):
    profile_books = "https://akademik.yok.gov.tr/AkademikArama/AkademisyenYayinBilgileri?" \
                    "pubType=q3SMeouSUM6tBWypaNs06Q&authorId=" + guid

    driver.get(profile_books)
    go_sleep()

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if 'The requested URL was rejected. Please consult with your administrator.' in soup.find('body'):
        logging.error(f"{guid} için kitap sayfasına erişim reddedildi.")
        return

    books = soup.find('div', {'class': 'projects'})
    rows = books.find_all('div', {'class': 'row'})
    book_titles = []
    chapter_names = []
    years = []
    guid_list = []

    for row in rows:
        row_info = row.find('div', {'class': 'col-lg-11 col-md-10 col-sm-10 col-xs-9'})
        book_title = row_info.strong.text.split('.')[1].strip()
        book_titles.append(book_title.replace('\n', ' '))

        # Bölüm adını bul ve listeye ekle
        try:
            chapter_name = row_info.p.text.split("Bölüm Adı:")[1].split(",")[0].strip()
            chapter_names.append(chapter_name)
        except IndexError:
            chapter_names.append(row_info.strong.text.split('.')[1].strip())

        # Yılı bul ve listeye ekle
        year = row_info.find_all('span', {'class': 'label label-info'})[0].text.strip()
        years.append(year)
        guid_list.append(guid)

    # Listeleri bir DataFrame'e dönüştür
    df = pd.DataFrame({'guid': guid_list,
                       'Kitap Adı': book_titles,
                       'Bölüm Adı': chapter_names,
                       'Yıl': years})

    researcher_book_info_path = os.path.join(main_folder_path, "researcher_book_info.csv")
    if not os.path.exists(researcher_book_info_path):
        df.to_csv(researcher_book_info_path, index=False)
        logging.info(f"{researcher_book_info_path} oluşturuldu.")
    else:
        df.to_csv(researcher_book_info_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_book_info_path} güncellendi.")
        if len(df) == 0:
            logging.warning(f"{guid} için kitap bilgisi bulunamadı.")
    go_sleep()


def researcher_article_info_(guid, main_folder_path):
    article_path = "https://akademik.yok.gov.tr/AkademikArama/AkademisyenYayinBilgileri?" \
                   "pubType=5Eaxq5GEK5ukOf71Zpm7dA&authorId=" + guid
    driver.get(article_path)
    go_sleep()

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if 'The requested URL was rejected. Please consult with your administrator.' in soup.find('body'):
        logging.error(f"{guid} için makale sayfasına erişim reddedildi.")
        return

    tbody = soup.find('tbody')

    titles = []
    years = []
    details = []
    guid_list = []

    # Her bir tr etiketi için
    for tr in tbody.find_all('tr'):
        # Makale adını bul ve listeye ekle
        title = tr.find('a').text
        titles.append(title.replace('\n', ' '))

        # Yılı bul ve listeye ekle
        year = tr.find_all('td')[1].text
        year_match = re.search(r'\b\d{4}\b', year)
        if year_match is not None:
            years.append(year_match.group())
        else:
            years.append('Yıl Bilgisi Yok')

        # Detayları bul ve listeye ekle
        detail_elements = tr.find_all('span', {
            'class': ['label label-info', 'label label-primary', 'label label-success', 'label label-default']})
        detail_text = ' / '.join([elem.text.strip() for elem in detail_elements])
        details.append(detail_text.replace('\n', ' '))
        guid_list.append(guid)

    # Listeleri bir DataFrame'e dönüştür
    df = pd.DataFrame({'guid': guid_list, 'Makale Adı': titles, 'Yıl': years, 'Detaylar': details})

    researcher_article_info_path = os.path.join(main_folder_path, "researcher_article_info.csv")
    if not os.path.exists(researcher_article_info_path):
        df.to_csv(researcher_article_info_path, index=False)
        logging.info(f"{researcher_article_info_path} oluşturuldu.")
    else:
        df.to_csv(researcher_article_info_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_article_info_path} güncellendi.")
        if len(df) == 0:
            logging.warning(f"{guid} için makale bilgisi bulunamadı.")
    go_sleep()


def researcher_conference_info_(guid, main_folder_path):
    conference_path = "https://akademik.yok.gov.tr/AkademikArama/AkademisyenYayinBilgileri?" \
                      "pubType=iHDPgsbZ-szm5UHCxj3mmg&authorId=" + guid

    driver.get(conference_path)

    go_sleep()

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if 'The requested URL was rejected. Please consult with your administrator.' in soup.find('body'):
        logging.error(f"{guid} için bildiri sayfasına erişim reddedildi.")
        return

    tbody = soup.find('tbody')

    titles = []
    years = []
    details = []
    guid_list = []

    # Her bir tr etiketi için
    for tr in tbody.find_all('tr'):
        # Makale adını bul ve listeye ekle
        title = tr.find('a').text
        titles.append(title.replace('\n', ' '))

        # Yılı bul ve listeye ekle
        year = tr.find_all('td')[1].text
        year_match = re.search(r'\b\d{4}\b', year)
        if year_match is not None:
            years.append(year_match.group())
        else:
            years.append('Yıl Bilgisi Yok')

        # Detayları bul ve listeye ekle
        detail_elements = tr.find_all('span', {
            'class': ['label label-info', 'label label-primary', 'label label-success', 'label label-default']})
        detail_text = ' / '.join([elem.text.strip() for elem in detail_elements])
        details.append(detail_text.replace('\n', ' '))
        guid_list.append(guid)

    # Listeleri bir DataFrame'e dönüştür
    df = pd.DataFrame({'guid': guid_list, 'Kitap Adı': titles, 'Yıl': years, 'Detaylar': details})

    researcher_conference_info_path = os.path.join(main_folder_path, "researcher_conference_info.csv")
    if not os.path.exists(researcher_conference_info_path):
        df.to_csv(researcher_conference_info_path, index=False)
        logging.info(f"{researcher_conference_info_path} oluşturuldu.")
    else:
        df.to_csv(researcher_conference_info_path, index=False, mode='a', header=False)
        logging.info(f"{researcher_conference_info_path} güncellendi.")
        if len(df) == 0:
            logging.warning(f"{guid} için makale bilgisi bulunamadı.")
    go_sleep()


def main():
    print("Mevcut bir çalışma üzerinden çalışabilir veya yeni bir anahtar kelime ile aramaya yapabilirsiniz.")
    print("1 - Mevcut çalışma üzerinden devam et")
    print("2 - Yeni bir arama yap")
    choice = input("Seçiminiz: ")
    if choice == "1":
        keyword = input("Mevcut Çalışma klasörünün adını girin: ")
        main_folder_path, config_folder_path = folder_creation_(keyword)
        scrape_profiles_(main_folder_path, config_folder_path)
    else:
        keyword = input("Aramak istediğiniz anahtar kelimeyi girin: ")
        main_folder_path, config_folder_path = folder_creation_(keyword)
        search_url = search_academic_by_keyword_(keyword)
        search_page_(search_url, config_folder_path)
        print("Profiller alındı. Bütün profilleri şimdi almak istiyor musunuz?")
        print("1 - Evet")
        print("2 - Hayır")
        choice = input("Seçiminiz: ")
        if choice == "1":
            scrape_profiles_(main_folder_path, config_folder_path)
        else:
            print("Program sonlandırıldı.")


if __name__ == '__main__':
    main()
