import pandas as pd
import os

# قراءة البيانات
df = pd.read_csv("data/raw/wuzzuf_all_jobs.csv")

print("Before cleaning:", df.shape)

# حذف التكرار
df = df.drop_duplicates(subset=["link"])

# حذف الصفوف الفاضية المهمة
df = df.dropna(subset=["title", "company", "link"])

# تنظيف النصوص
for col in df.columns:
    df[col] = df[col].astype(str).str.strip()

# حفظ البيانات النظيفة
os.makedirs("data/processed", exist_ok=True)
df.to_csv("data/processed/wuzzuf_jobs_cleaned.csv", index=False, encoding="utf-8-sig")

print("After cleaning:", df.shape)
print("Cleaned file saved.")
print(df.head())