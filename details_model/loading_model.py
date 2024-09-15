import joblib
import numpy as np
import re
from sklearn.metrics.pairwise import cosine_similarity

# Load the saved models and reduced matrix
tfidf_vectorizer = joblib.load('./details_model/tfidf_vectorizer.joblib')
svd = joblib.load('./details_model/svd.joblib')
tfidf_matrix_reduced = joblib.load('./details_model/tfidf_matrix_reduced.joblib')
df = joblib.load('./details_model/df.joblib')

# Function to clean the text (removes numbers and special characters)
def clean_text(text):
    text = re.sub(r'\d+', '', text)  # Remove digits
    text = re.sub(r'\W+', ' ', text)  # Remove special characters
    text = text.lower().strip()  # Convert to lowercase and strip
    return text

# Function to find the most similar transaction
def find_most_similar(test_description):
    # Clean the test description
    test_combined = clean_text(test_description)
    
    # Transform the test description into the TF-IDF vector space
    test_vector = tfidf_vectorizer.transform([test_combined])
    
    # Reduce dimensionality of the test vector using SVD
    test_vector_reduced = svd.transform(test_vector)
    
    # Use matrix multiplication for faster cosine similarity calculation
    similarity_scores = np.dot(tfidf_matrix_reduced, test_vector_reduced.T).flatten()
    
    # Find the index of the most similar transaction
    most_similar_index = similarity_scores.argmax()
    
    # Get the most similar transaction description, its similarity score, and other relevant columns
    most_similar_row = df.iloc[most_similar_index]
    similarity_score = similarity_scores[most_similar_index] * 100  # Convert to percentage
    
    return most_similar_row, similarity_score



# Example usage
test_description = "BINBIN"
most_similar_row, similarity_score = find_most_similar(test_description)

# # Print the result
# print(f"Test Description: {test_description}")
# print(f"Most Similar Transaction: {most_similar_row['transaction_description']}")
# print(f"Segment: {most_similar_row['segment']}")
# print(f"Type: {most_similar_row['type']}")
# print(f"Sub_Type: {most_similar_row['sub_type']}")
# print(f"Category: {most_similar_row['category']}")
# print(f"Sub_category: {most_similar_row['sub_category']}")
# print(f"Location_used: {most_similar_row['country_used']}")

# print(f"Similarity Score: {similarity_score:.2f}%")
