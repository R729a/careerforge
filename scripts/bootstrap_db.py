import sqlite3
import os
import uuid

DB_PATH = "careerforge.db"
SCHEMA_PATH = os.path.join("db", "schema.sql")

def run():
    print(f"Bootstrapping local SQLite database at: {DB_PATH}")
    
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    # Read schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Connect and run
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Execute schema script
        cursor.executescript(schema_sql)
        conn.commit()
        print("Schema successfully applied.")
        
        # Check if seed data already exists
        cursor.execute("SELECT COUNT(*) FROM skills")
        if cursor.fetchone()[0] == 0:
            print("Seeding skills database...")
            skills_data = [
                (str(uuid.uuid4()), "Python", "General-purpose programming language for ML and scripting.", "Programming"),
                (str(uuid.uuid4()), "SQL", "Structured Query Language for querying databases.", "Data Analysis"),
                (str(uuid.uuid4()), "Machine Learning", "Core ML principles, supervised/unsupervised learning, and algorithms.", "Data Science"),
                (str(uuid.uuid4()), "Deep Learning", "Neural networks, CNNs, RNNs, and framework implementation.", "Data Science"),
                (str(uuid.uuid4()), "PyTorch", "Open-source machine learning library developed by Meta's AI Research lab.", "Frameworks"),
                (str(uuid.uuid4()), "TensorFlow", "End-to-end open-source platform for machine learning by Google.", "Frameworks"),
                (str(uuid.uuid4()), "Docker", "Containerization platform to build, ship, and run applications.", "DevOps"),
                (str(uuid.uuid4()), "FastAPI", "Modern, fast web framework for building APIs with Python.", "Backend Development"),
                (str(uuid.uuid4()), "Data Engineering", "Data pipelining, ETL processes, and database management.", "Data Engineering"),
                (str(uuid.uuid4()), "Git & GitHub", "Version control systems for collaborative software engineering.", "Software Engineering")
            ]
            cursor.executemany("INSERT INTO skills (id, name, description, category) VALUES (?, ?, ?, ?)", skills_data)
            conn.commit()
            print("Skills successfully seeded.")
            
        cursor.execute("SELECT COUNT(*) FROM courses")
        if cursor.fetchone()[0] == 0:
            print("Seeding courses database...")
            courses_data = [
                (str(uuid.uuid4()), "Introduction to Python Programming", "Master the basics of Python syntax, data types, and loops.", "Coursera", "https://coursera.org/intro-python", "Python,Git & GitHub"),
                (str(uuid.uuid4()), "Machine Learning Specialization", "Learn foundational ML concepts under Andrew Ng.", "Coursera", "https://coursera.org/ml-specialization", "Machine Learning,Python"),
                (str(uuid.uuid4()), "Deep Learning with PyTorch", "Step-by-step neural networks deployment in PyTorch.", "Udemy", "https://udemy.com/pytorch-dl", "Deep Learning,PyTorch,Python"),
                (str(uuid.uuid4()), "Complete SQL Bootcamp", "Query databases, perform analysis, and master joins/subqueries.", "Udemy", "https://udemy.com/sql-bootcamp", "SQL"),
                (str(uuid.uuid4()), "FastAPI Web Development Masterclass", "Build high-performance REST APIs with python.", "Udemy", "https://udemy.com/fastapi-masterclass", "FastAPI,Python"),
                (str(uuid.uuid4()), "Docker for DevOps Engineers", "Build, debug, and orchestrate containers locally.", "Coursera", "https://coursera.org/docker-devops", "Docker,DevOps")
            ]
            cursor.executemany("INSERT INTO courses (id, title, description, provider, url, skills_taught) VALUES (?, ?, ?, ?, ?, ?)", courses_data)
            conn.commit()
            print("Courses successfully seeded.")
            
    except Exception as e:
        print(f"Error during bootstrap: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run()
