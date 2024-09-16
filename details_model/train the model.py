import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import re
import joblib

# Load your dataset
df = pd.read_csv('./details_model/Model Sample Data 16.09.2024.csv')

# Filter out transactions with empty details
df = df.dropna(subset=['transaction_description']).reset_index(drop=True)

# Function to clean the text (removes numbers and special characters)
def clean_text(text):
    text = re.sub(r'\d+', '', text)  # Remove digits
    text = re.sub(r'\W+', ' ', text)  # Remove special characters
    text = text.lower().strip()  # Convert to lowercase and strip
    return text

# Clean the transaction descriptions and concatenate relevant columns
df['Combined'] = df.apply(lambda row: f"{clean_text(row['transaction_description'])} "
                                      f"{clean_text(str(row['segment']))} "
                                      f"{clean_text(str(row['type']))} "
                                      f"{clean_text(str(row['sub_type']))} "
                                      f"{clean_text(str(row['category']))} "
                                      f"{clean_text(str(row['sub_category']))}"
                                      f"{clean_text(str(row['country_used']))}", axis=1)

# Vectorization using TF-IDF
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(df['Combined'])

# Reduce dimensionality with Truncated SVD
n_components = 100  # You can adjust this number for better performance
svd = TruncatedSVD(n_components=n_components)
tfidf_matrix_reduced = svd.fit_transform(tfidf_matrix)

# Save the model, SVD, and reduced tfidf matrix
joblib.dump(tfidf_vectorizer, 'tfidf_vectorizer.joblib')
joblib.dump(svd, 'svd.joblib')
joblib.dump(tfidf_matrix_reduced, 'tfidf_matrix_reduced.joblib')
joblib.dump(df, 'df.joblib')  # Save the DataFrame for future use
