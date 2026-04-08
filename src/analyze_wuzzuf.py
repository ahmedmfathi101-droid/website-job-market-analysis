import os
import re
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt


# =========================
# 1) SETTINGS
# =========================
INPUT_FILE = "data/processed/wuzzuf_jobs_cleaned.csv"
OUTPUT_DIR = "outputs"
SUMMARY_FILE = os.path.join(OUTPUT_DIR, "summary_report.txt")
SKILLS_FILE = os.path.join(OUTPUT_DIR, "skills_frequency.csv")
STATS_FILE = os.path.join(OUTPUT_DIR, "general_statistics.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# 2) LOAD DATA
# =========================
df = pd.read_csv(INPUT_FILE)

print("=" * 80)
print("RAW DATA LOADED")
print("=" * 80)
print(df.head())
print("\nShape before in-analysis cleaning:", df.shape)


# =========================
# 3) LIGHT CLEANING (safety layer)
# =========================
# نخلي أسماء الأعمدة lower-case لو حبيت تتفادى مشاكل مستقبلية
df.columns = [col.strip().lower() for col in df.columns]

# إزالة التكرار
if "link" in df.columns:
    df = df.drop_duplicates(subset=["link"])
else:
    df = df.drop_duplicates()

# حذف الصفوف اللي ناقصة في أهم الأعمدة
required_cols = [col for col in ["title", "company", "location", "link"] if col in df.columns]
if required_cols:
    df = df.dropna(subset=required_cols)

# تنظيف النصوص
for col in df.columns:
    df[col] = df[col].astype(str).str.strip()

# استبدال nan النصية
df = df.replace({"nan": "N/A", "None": "N/A", "": "N/A"})

print("Shape after in-analysis cleaning:", df.shape)
print()


# =========================
# 4) HELPER FUNCTIONS
# =========================
def save_bar_chart(series, title, xlabel, ylabel, filename, rotation=45, top_n=None):
    """
    Save a bar chart from a pandas Series.
    """
    if top_n is not None:
        series = series.head(top_n)

    plt.figure(figsize=(12, 6))
    series.plot(kind="bar")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename))
    plt.close()


def save_pie_chart(series, title, filename):
    """
    Save a pie chart from a pandas Series.
    """
    plt.figure(figsize=(8, 8))
    series.plot(kind="pie", autopct="%1.1f%%")
    plt.title(title)
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename))
    plt.close()


def write_section(file_obj, section_title, content_lines):
    file_obj.write(f"\n{'=' * 80}\n")
    file_obj.write(f"{section_title}\n")
    file_obj.write(f"{'=' * 80}\n")
    for line in content_lines:
        file_obj.write(f"{line}\n")


def value_counts_safe(dataframe, column_name, top_n=None):
    """
    Return value_counts for a column if it exists.
    """
    if column_name not in dataframe.columns:
        return pd.Series(dtype="int64")
    result = dataframe[column_name].value_counts()
    if top_n is not None:
        return result.head(top_n)
    return result


def contains_keywords(series, keywords):
    """
    Returns boolean mask where any keyword exists in text series.
    """
    pattern = "|".join(keywords)
    return series.str.contains(pattern, case=False, na=False, regex=True)


def parse_experience_to_avg(exp_text):
    """
    يحول نص الخبرة إلى رقم متوسط تقريبي.
    Examples:
    '3 - 5 Yrs of Exp' -> 4.0
    '10+ Yrs of Exp' -> 10.0
    """
    exp_text = str(exp_text).strip()

    # range case: 3 - 5
    match_range = re.search(r"(\d+)\s*-\s*(\d+)", exp_text)
    if match_range:
        low = int(match_range.group(1))
        high = int(match_range.group(2))
        return (low + high) / 2

    # plus case: 10+
    match_plus = re.search(r"(\d+)\+", exp_text)
    if match_plus:
        return float(match_plus.group(1))

    # single number
    match_single = re.search(r"(\d+)", exp_text)
    if match_single:
        return float(match_single.group(1))

    return None


def extract_top_words_from_tags(tag_series, top_n=20):
    """
    استخراج أكثر الكلمات تكرارًا من عمود tags.
    """
    all_words = []

    stop_words = {
        "and", "or", "the", "of", "in", "to", "for", "with", "on", "at",
        "a", "an", "is", "as", "from", "by", "full", "time", "part",
        "yrs", "exp", "years", "year"
    }

    for row in tag_series.dropna():
        text = str(row).lower()
        # نفصل بالكومات والرموز
        parts = re.split(r"[,/|•\-]+", text)
        for part in parts:
            word = part.strip()
            if word and word not in stop_words and len(word) > 2:
                all_words.append(word)

    return Counter(all_words).most_common(top_n)


# =========================
# 5) GENERAL STATISTICS
# =========================
total_jobs = len(df)
total_unique_titles = df["title"].nunique() if "title" in df.columns else 0
total_unique_companies = df["company"].nunique() if "company" in df.columns else 0
total_unique_locations = df["location"].nunique() if "location" in df.columns else 0

experience_avg = None
if "experience_years" in df.columns:
    exp_numeric = df["experience_years"].apply(parse_experience_to_avg)
    exp_numeric = pd.to_numeric(exp_numeric, errors="coerce")
    if exp_numeric.notna().sum() > 0:
        experience_avg = round(exp_numeric.mean(), 2)

general_stats = pd.DataFrame({
    "metric": [
        "total_jobs",
        "unique_job_titles",
        "unique_companies",
        "unique_locations",
        "average_required_experience_years"
    ],
    "value": [
        total_jobs,
        total_unique_titles,
        total_unique_companies,
        total_unique_locations,
        experience_avg if experience_avg is not None else "N/A"
    ]
})

general_stats.to_csv(STATS_FILE, index=False, encoding="utf-8-sig")

print("=" * 80)
print("GENERAL STATISTICS")
print("=" * 80)
print(general_stats)
print()


# =========================
# 6) TOP COUNTS
# =========================
top_titles = value_counts_safe(df, "title", top_n=10)
top_companies = value_counts_safe(df, "company", top_n=10)
top_locations = value_counts_safe(df, "location", top_n=10)
employment_dist = value_counts_safe(df, "employment_type")
work_setup_dist = value_counts_safe(df, "work_setup")
career_level_dist = value_counts_safe(df, "career_level")
experience_dist = value_counts_safe(df, "experience_years", top_n=10)

print("=" * 80)
print("TOP TITLES")
print("=" * 80)
print(top_titles)
print()

print("=" * 80)
print("TOP COMPANIES")
print("=" * 80)
print(top_companies)
print()

print("=" * 80)
print("TOP LOCATIONS")
print("=" * 80)
print(top_locations)
print()

print("=" * 80)
print("EMPLOYMENT TYPE DISTRIBUTION")
print("=" * 80)
print(employment_dist)
print()

print("=" * 80)
print("WORK SETUP DISTRIBUTION")
print("=" * 80)
print(work_setup_dist)
print()

print("=" * 80)
print("CAREER LEVEL DISTRIBUTION")
print("=" * 80)
print(career_level_dist)
print()

print("=" * 80)
print("EXPERIENCE DISTRIBUTION")
print("=" * 80)
print(experience_dist)
print()


# =========================
# 7) SAVE CHARTS
# =========================
if not top_titles.empty:
    save_bar_chart(
        top_titles,
        "Top 10 Job Titles",
        "Job Title",
        "Count",
        "top_titles.png"
    )

if not top_companies.empty:
    save_bar_chart(
        top_companies,
        "Top 10 Companies",
        "Company",
        "Count",
        "top_companies.png"
    )

if not top_locations.empty:
    save_bar_chart(
        top_locations,
        "Top 10 Locations",
        "Location",
        "Count",
        "top_locations.png"
    )

if not employment_dist.empty:
    save_bar_chart(
        employment_dist,
        "Employment Type Distribution",
        "Employment Type",
        "Count",
        "employment_type_distribution.png"
    )
    save_pie_chart(
        employment_dist,
        "Employment Type Distribution",
        "employment_type_distribution_pie.png"
    )

if not work_setup_dist.empty:
    save_bar_chart(
        work_setup_dist,
        "Work Setup Distribution",
        "Work Setup",
        "Count",
        "work_setup_distribution.png"
    )
    save_pie_chart(
        work_setup_dist,
        "Work Setup Distribution",
        "work_setup_distribution_pie.png"
    )

if not career_level_dist.empty:
    save_bar_chart(
        career_level_dist,
        "Career Level Distribution",
        "Career Level",
        "Count",
        "career_level_distribution.png"
    )

if not experience_dist.empty:
    save_bar_chart(
        experience_dist,
        "Top 10 Experience Requirements",
        "Experience Range",
        "Count",
        "experience_distribution.png"
    )


# =========================
# 8) SKILLS ANALYSIS
# =========================
skills_to_check = [
    "python", "sql", "excel", "power bi", "tableau",
    "communication", "sales", "pharmacist", "medical",
    "data analysis", "reporting", "customer service",
    "problem solving", "team leadership"
]

skills_counts = []

source_col_for_skills = None
if "tags" in df.columns:
    source_col_for_skills = "tags"
elif "title" in df.columns:
    source_col_for_skills = "title"

if source_col_for_skills:
    for skill in skills_to_check:
        count = df[source_col_for_skills].str.lower().str.contains(skill, na=False).sum()
        percentage = round((count / total_jobs) * 100, 2) if total_jobs > 0 else 0
        skills_counts.append({
            "skill": skill,
            "count": count,
            "percentage_of_jobs": percentage
        })

skills_df = pd.DataFrame(skills_counts).sort_values(by="count", ascending=False)
skills_df.to_csv(SKILLS_FILE, index=False, encoding="utf-8-sig")

print("=" * 80)
print("SKILLS FREQUENCY")
print("=" * 80)
print(skills_df)
print()

if not skills_df.empty:
    plt.figure(figsize=(12, 6))
    plt.bar(skills_df["skill"], skills_df["count"])
    plt.title("Skills Frequency")
    plt.xlabel("Skill")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "skills_frequency.png"))
    plt.close()


# =========================
# 9) TOP WORDS IN TAGS
# =========================
top_tag_words = []
if "tags" in df.columns:
    top_tag_words = extract_top_words_from_tags(df["tags"], top_n=20)
    top_tag_words_df = pd.DataFrame(top_tag_words, columns=["word", "count"])
    top_tag_words_df.to_csv(
        os.path.join(OUTPUT_DIR, "top_tag_words.csv"),
        index=False,
        encoding="utf-8-sig"
    )

    if not top_tag_words_df.empty:
        plt.figure(figsize=(12, 6))
        plt.bar(top_tag_words_df["word"], top_tag_words_df["count"])
        plt.title("Top 20 Most Frequent Words in Tags")
        plt.xlabel("Word")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "top_tag_words.png"))
        plt.close()


# =========================
# 10) PHARMA / MEDICAL JOBS ANALYSIS
# =========================
pharma_keywords = ["pharma", "medical", "pharmacist", "regulatory", "healthcare"]
pharma_jobs = pd.DataFrame()

if "title" in df.columns:
    pharma_jobs = df[contains_keywords(df["title"], pharma_keywords)]

pharma_count = len(pharma_jobs)
pharma_percentage = round((pharma_count / total_jobs) * 100, 2) if total_jobs > 0 else 0

pharma_top_titles = value_counts_safe(pharma_jobs, "title", top_n=10)
pharma_top_companies = value_counts_safe(pharma_jobs, "company", top_n=10)
pharma_top_locations = value_counts_safe(pharma_jobs, "location", top_n=10)

print("=" * 80)
print("PHARMA / MEDICAL JOBS ANALYSIS")
print("=" * 80)
print(f"Pharma/Medical jobs count: {pharma_count}")
print(f"Pharma/Medical jobs percentage: {pharma_percentage}%")
print("\nTop Pharma Titles:")
print(pharma_top_titles)
print("\nTop Pharma Companies:")
print(pharma_top_companies)
print("\nTop Pharma Locations:")
print(pharma_top_locations)
print()

if not pharma_top_titles.empty:
    save_bar_chart(
        pharma_top_titles,
        "Top Pharma / Medical Job Titles",
        "Job Title",
        "Count",
        "pharma_top_titles.png"
    )

if not pharma_top_companies.empty:
    save_bar_chart(
        pharma_top_companies,
        "Top Pharma / Medical Companies",
        "Company",
        "Count",
        "pharma_top_companies.png"
    )

if not pharma_top_locations.empty:
    save_bar_chart(
        pharma_top_locations,
        "Top Pharma / Medical Locations",
        "Location",
        "Count",
        "pharma_top_locations.png"
    )


# =========================
# 11) DATA JOBS ANALYSIS
# =========================
data_keywords = ["data", "analyst", "bi", "business intelligence", "sql", "reporting"]
data_jobs = pd.DataFrame()

if "title" in df.columns:
    data_jobs = df[contains_keywords(df["title"], data_keywords)]

data_count = len(data_jobs)
data_percentage = round((data_count / total_jobs) * 100, 2) if total_jobs > 0 else 0

data_top_titles = value_counts_safe(data_jobs, "title", top_n=10)
data_top_companies = value_counts_safe(data_jobs, "company", top_n=10)
data_top_locations = value_counts_safe(data_jobs, "location", top_n=10)

print("=" * 80)
print("DATA JOBS ANALYSIS")
print("=" * 80)
print(f"Data jobs count: {data_count}")
print(f"Data jobs percentage: {data_percentage}%")
print("\nTop Data Titles:")
print(data_top_titles)
print("\nTop Data Companies:")
print(data_top_companies)
print("\nTop Data Locations:")
print(data_top_locations)
print()

if not data_top_titles.empty:
    save_bar_chart(
        data_top_titles,
        "Top Data Job Titles",
        "Job Title",
        "Count",
        "data_top_titles.png"
    )

if not data_top_companies.empty:
    save_bar_chart(
        data_top_companies,
        "Top Data Companies",
        "Company",
        "Count",
        "data_top_companies.png"
    )

if not data_top_locations.empty:
    save_bar_chart(
        data_top_locations,
        "Top Data Locations",
        "Location",
        "Count",
        "data_top_locations.png"
    )


# =========================
# 12) DATA VS PHARMA COMPARISON
# =========================
comparison_df = pd.DataFrame({
    "category": ["All Jobs", "Pharma/Medical Jobs", "Data Jobs"],
    "count": [total_jobs, pharma_count, data_count],
    "percentage_of_total": [
        100.0 if total_jobs > 0 else 0,
        pharma_percentage,
        data_percentage
    ]
})

comparison_df.to_csv(
    os.path.join(OUTPUT_DIR, "data_vs_pharma_comparison.csv"),
    index=False,
    encoding="utf-8-sig"
)

plt.figure(figsize=(8, 6))
plt.bar(comparison_df["category"], comparison_df["count"])
plt.title("All Jobs vs Pharma Jobs vs Data Jobs")
plt.xlabel("Category")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "data_vs_pharma_comparison.png"))
plt.close()

print("=" * 80)
print("DATA VS PHARMA COMPARISON")
print("=" * 80)
print(comparison_df)
print()


# =========================
# 13) SUMMARY REPORT
# =========================
summary_lines_general = [
    f"Total scraped jobs: {total_jobs}",
    f"Unique job titles: {total_unique_titles}",
    f"Unique companies: {total_unique_companies}",
    f"Unique locations: {total_unique_locations}",
    f"Average required experience (approx): {experience_avg if experience_avg is not None else 'N/A'} years"
]

summary_lines_titles = [f"{idx + 1}. {title} -> {count}" for idx, (title, count) in enumerate(top_titles.items())]
summary_lines_companies = [f"{idx + 1}. {company} -> {count}" for idx, (company, count) in enumerate(top_companies.items())]
summary_lines_locations = [f"{idx + 1}. {location} -> {count}" for idx, (location, count) in enumerate(top_locations.items())]
summary_lines_employment = [f"{k} -> {v}" for k, v in employment_dist.items()]
summary_lines_work_setup = [f"{k} -> {v}" for k, v in work_setup_dist.items()]
summary_lines_career = [f"{k} -> {v}" for k, v in career_level_dist.items()]
summary_lines_experience = [f"{k} -> {v}" for k, v in experience_dist.items()]

summary_lines_skills = []
if not skills_df.empty:
    for _, row in skills_df.iterrows():
        summary_lines_skills.append(
            f"{row['skill']} -> {row['count']} jobs ({row['percentage_of_jobs']}%)"
        )

summary_lines_pharma = [
    f"Pharma/Medical jobs count: {pharma_count}",
    f"Pharma/Medical jobs percentage of total: {pharma_percentage}%"
]
summary_lines_pharma += [f"{idx + 1}. {title} -> {count}" for idx, (title, count) in enumerate(pharma_top_titles.items())]

summary_lines_data = [
    f"Data jobs count: {data_count}",
    f"Data jobs percentage of total: {data_percentage}%"
]
summary_lines_data += [f"{idx + 1}. {title} -> {count}" for idx, (title, count) in enumerate(data_top_titles.items())]

summary_lines_comparison = [
    f"All Jobs -> {total_jobs}",
    f"Pharma/Medical Jobs -> {pharma_count} ({pharma_percentage}%)",
    f"Data Jobs -> {data_count} ({data_percentage}%)"
]

with open(SUMMARY_FILE, "w", encoding="utf-8-sig") as f:
    write_section(f, "GENERAL STATISTICS", summary_lines_general)
    write_section(f, "TOP 10 JOB TITLES", summary_lines_titles)
    write_section(f, "TOP 10 COMPANIES", summary_lines_companies)
    write_section(f, "TOP 10 LOCATIONS", summary_lines_locations)
    write_section(f, "EMPLOYMENT TYPE DISTRIBUTION", summary_lines_employment)
    write_section(f, "WORK SETUP DISTRIBUTION", summary_lines_work_setup)
    write_section(f, "CAREER LEVEL DISTRIBUTION", summary_lines_career)
    write_section(f, "EXPERIENCE DISTRIBUTION", summary_lines_experience)
    write_section(f, "SKILLS FREQUENCY", summary_lines_skills)
    write_section(f, "PHARMA / MEDICAL JOBS ANALYSIS", summary_lines_pharma)
    write_section(f, "DATA JOBS ANALYSIS", summary_lines_data)
    write_section(f, "DATA VS PHARMA COMPARISON", summary_lines_comparison)

    if top_tag_words:
        tag_word_lines = [f"{word} -> {count}" for word, count in top_tag_words]
        write_section(f, "TOP WORDS IN TAGS", tag_word_lines)


# =========================
# 14) OPTIONAL: SAVE FILTERED DATASETS
# =========================
if not pharma_jobs.empty:
    pharma_jobs.to_csv(
        os.path.join(OUTPUT_DIR, "pharma_jobs_filtered.csv"),
        index=False,
        encoding="utf-8-sig"
    )

if not data_jobs.empty:
    data_jobs.to_csv(
        os.path.join(OUTPUT_DIR, "data_jobs_filtered.csv"),
        index=False,
        encoding="utf-8-sig"
    )


# =========================
# 15) FINAL PRINTS
# =========================
print("=" * 80)
print("ANALYSIS COMPLETED SUCCESSFULLY")
print("=" * 80)
print(f"Summary report saved to: {SUMMARY_FILE}")
print(f"General statistics saved to: {STATS_FILE}")
print(f"Skills frequency saved to: {SKILLS_FILE}")
print(f"All charts and extra files saved in: {OUTPUT_DIR}")