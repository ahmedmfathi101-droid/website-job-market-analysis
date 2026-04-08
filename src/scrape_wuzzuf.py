import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time

headers = {
    "User-Agent": "Mozilla/5.0"
}

all_jobs = []
start = 0

while True:
    url = f"https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt&start={start}"
    print(f"Scraping start={start}")

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"Stopped بسبب status code = {response.status_code}")
        break

    soup = BeautifulSoup(response.text, "html.parser")

    job_headers = soup.find_all("div", class_="css-lptxge")
    job_details = soup.find_all("div", class_="css-1rhj4yg")

    if len(job_headers) == 0 or len(job_details) == 0:
        print("No jobs found. Stopping.")
        break

    page_jobs = 0

    for i in range(min(len(job_headers), len(job_details))):
        header = job_headers[i]
        detail = job_details[i]

        title_tag = header.find("a", class_="css-o171kl")
        company_tag = header.find("a", class_="css-ipsyv7")
        location_tag = header.find("span", class_="css-16x61xq")
        posted_tag = header.find("div", class_="css-eg55jf")

        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        link = "https://wuzzuf.net" + title_tag["href"] if title_tag and title_tag.has_attr("href") else "N/A"
        company = company_tag.get_text(strip=True).replace("-", "").strip() if company_tag else "N/A"
        location = location_tag.get_text(strip=True) if location_tag else "N/A"
        posted_time = posted_tag.get_text(strip=True) if posted_tag else "N/A"

        top_detail_div = detail.find("div", class_="css-5jhz9n")
        top_spans = top_detail_div.find_all("span") if top_detail_div else []

        employment_type = top_spans[0].get_text(strip=True) if len(top_spans) > 0 else "N/A"
        work_setup = top_spans[1].get_text(strip=True) if len(top_spans) > 1 else "N/A"

        all_links = detail.find_all("a")
        all_spans = detail.find_all("span")

        career_level = "N/A"
        experience_years = "N/A"
        tags = []

        if len(all_links) >= 3:
            career_level = all_links[2].get_text(strip=True).replace("·", "").strip()

        for span in all_spans:
            text = span.get_text(strip=True)
            if "Yrs of Exp" in text:
                experience_years = text.replace("·", "").strip()

        for a in all_links[3:]:
            tag_text = a.get_text(strip=True).replace("·", "").strip()
            if tag_text:
                tags.append(tag_text)

        all_jobs.append({
            "start": start,
            "title": title,
            "company": company,
            "location": location,
            "posted_time": posted_time,
            "employment_type": employment_type,
            "work_setup": work_setup,
            "career_level": career_level,
            "experience_years": experience_years,
            "tags": ", ".join(tags),
            "link": link
        })

        page_jobs += 1

    print(f"Extracted {page_jobs} jobs from start={start}")

    start += 1
    time.sleep(2)

df = pd.DataFrame(all_jobs)

df = df.drop_duplicates(subset=["link"])
df = df.drop_duplicates()

os.makedirs("data/raw", exist_ok=True)
df.to_csv("data/raw/wuzzuf_all_jobs.csv", index=False, encoding="utf-8-sig")

print("\nDone.")
print("Total jobs:", len(df))
print(df.head())