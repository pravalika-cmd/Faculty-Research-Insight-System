from flask import Flask, render_template, request, jsonify
import mysql.connector

app = Flask(__name__)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Root@123",
    database="research_insight_db"
)

print("DB CONNECTED:", db.is_connected())

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -----------------------------
# DOMAIN SEARCH
# -----------------------------
@app.route("/domain")
def domain_search():
    domain = request.args.get("name")
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT p.title,
           IFNULL(GROUP_CONCAT(DISTINCT f.faculty_name), 'Unknown Author') AS authors,
           p.publication_year
    FROM Publication p
    JOIN Research_Domain r ON p.domain_id = r.domain_id
    LEFT JOIN Faculty_Publication fp ON p.publication_id = fp.publication_id
    LEFT JOIN Faculty f ON fp.faculty_id = f.faculty_id
    WHERE r.domain_name LIKE %s
    GROUP BY p.publication_id
    ORDER BY p.publication_year DESC;
    """
    cursor.execute(query, (f"%{domain}%",))
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# KEYWORD SEARCH
# -----------------------------
@app.route("/keyword")
def keyword_search():
    keyword = request.args.get("key")
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT p.title,
           IFNULL(GROUP_CONCAT(DISTINCT f.faculty_name), 'Unknown Author') AS authors,
           p.publication_year
    FROM Publication p
    LEFT JOIN Faculty_Publication fp ON p.publication_id = fp.publication_id
    LEFT JOIN Faculty f ON fp.faculty_id = f.faculty_id
    WHERE p.title LIKE %s
    GROUP BY p.publication_id
    ORDER BY p.publication_year DESC;
    """
    cursor.execute(query, (f"%{keyword}%",))
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# TOPIC SEARCH
# -----------------------------
@app.route("/topic")
def topic_search():
    topic = request.args.get("name")
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT p.title,
           IFNULL(GROUP_CONCAT(DISTINCT f.faculty_name), 'Unknown Author') AS authors,
           p.publication_year
    FROM Publication p
    LEFT JOIN Faculty_Publication fp ON p.publication_id = fp.publication_id
    LEFT JOIN Faculty f ON fp.faculty_id = f.faculty_id
    WHERE p.title LIKE %s
    GROUP BY p.publication_id
    ORDER BY p.publication_year DESC;
    """
    cursor.execute(query, (f"%{topic}%",))
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# YEAR ANALYTICS
# -----------------------------
@app.route("/analytics/year")
def year_analytics():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT publication_year, COUNT(*) AS total
        FROM Publication
        GROUP BY publication_year
        ORDER BY publication_year
    """)
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# DOMAIN ANALYTICS
# -----------------------------
@app.route("/analytics/domain")
def domain_analytics():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.domain_name, p.publication_year, COUNT(*) AS total
        FROM Publication p
        JOIN Research_Domain r ON p.domain_id = r.domain_id
        GROUP BY r.domain_name, p.publication_year
    """)
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# TOP AUTHORS
# -----------------------------
@app.route("/analytics/top-authors")
def top_authors():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.faculty_name, COUNT(fp.publication_id) AS total_publications
        FROM Faculty f
        JOIN Faculty_Publication fp ON f.faculty_id = fp.faculty_id
        GROUP BY f.faculty_id
        ORDER BY total_publications DESC
        LIMIT 5
    """)
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

# -----------------------------
# RESEARCH GAP
# -----------------------------
@app.route("/analytics/research-gap")
def research_gap():
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT r.domain_name, p.publication_year, COUNT(*) AS total
    FROM Publication p
    JOIN Research_Domain r ON p.domain_id = r.domain_id
    GROUP BY r.domain_name, p.publication_year
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    domain_stats = {}

    for row in rows:
        domain = row["domain_name"]
        year = row["publication_year"]
        count = row["total"]

        domain_stats.setdefault(domain, {})[year] = count

    results = []

    for domain, years in domain_stats.items():
        sorted_years = sorted(years.keys())

        if len(sorted_years) < 2:
            growth = 0
        else:
            growth = years[sorted_years[-1]] - years[sorted_years[0]]

        total_papers = sum(years.values())

        # 🔥 IMPROVED CLASSIFICATION
        if total_papers >= 6 and growth <= 1:
            status = "Stable"
        elif growth >= 3:
            status = "Emerging"
        else:
            status = "Research Gap"

        results.append({
            "domain": domain,
            "total_papers": total_papers,
            "growth": growth,
            "status": status
        })

    return jsonify(results)


# -----------------------------
# INFLUENCE SCORE
# -----------------------------
@app.route("/analytics/influence")
def influence():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.faculty_name,
               COUNT(fp.publication_id) AS total_publications,
               SUM(CASE WHEN p.publication_year >= YEAR(CURDATE()) - 2 THEN 1 ELSE 0 END) AS recent
        FROM Faculty f
        JOIN Faculty_Publication fp ON f.faculty_id = fp.faculty_id
        JOIN Publication p ON fp.publication_id = p.publication_id
        GROUP BY f.faculty_id
    """)
    data = cursor.fetchall()
    cursor.close()

    for d in data:
        d["influence_score"] = d["total_publications"] + 2 * d["recent"]

    return jsonify(sorted(data, key=lambda x: x["influence_score"], reverse=True))

# -----------------------------
# DOMAIN–AUTHOR NETWORK
# -----------------------------
@app.route("/analytics/network")
def network():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.faculty_name, r.domain_name, COUNT(*) AS papers
        FROM Faculty f
        JOIN Faculty_Publication fp ON f.faculty_id = fp.faculty_id
        JOIN Publication p ON fp.publication_id = p.publication_id
        JOIN Research_Domain r ON p.domain_id = r.domain_id
        GROUP BY f.faculty_name, r.domain_name
    """)
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)

@app.route("/analytics/paper-quality")
def paper_quality():
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT 
        p.title,
        r.domain_name,
        COALESCE(pq.quartile, 'Not Indexed') AS quartile
    FROM Publication p
    JOIN Research_Domain r ON p.domain_id = r.domain_id
    LEFT JOIN Publication_Quality pq 
           ON p.publication_id = pq.publication_id
    ORDER BY r.domain_name;
    """

    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
