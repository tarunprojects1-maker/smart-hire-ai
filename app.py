from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
from io import BytesIO
import fitz
import json
from dotenv import load_dotenv
from groq import Groq
from flask_sqlalchemy import SQLAlchemy

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import re

# LOAD ENV
load_dotenv()

# GROQ
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = Flask(__name__)

# SECRET KEY
app.secret_key = "smarthire_secret_key"

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

DB = SQLAlchemy(app)

# =========================
# USER TABLE
# =========================


class User(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    username = DB.Column(DB.String(100), nullable=False)

    email = DB.Column(DB.String(100), unique=True, nullable=False)

    password = DB.Column(DB.String(100), nullable=False)


# =========================
# ANALYSIS TABLE
# =========================


class Analysis(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    username = DB.Column(DB.String(100))

    filename = DB.Column(DB.String(200))

    ats_score = DB.Column(DB.String(20))

    match_percentage = DB.Column(DB.String(20))

    domain_match = DB.Column(DB.String(50))

    top_skills = DB.Column(DB.Text)

    missing_skills = DB.Column(DB.Text)

    suggestions = DB.Column(DB.Text)

    ai_result = DB.Column(DB.Text)

    job_roles = DB.Column(DB.Text)

    created_at = DB.Column(DB.DateTime, server_default=DB.func.now())


# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    DB.create_all()
    
# with app.app_context():
#     DB.create_all()

# =========================
# UPLOADS
# =========================

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# LOGIN CHECK
# =========================


def check_login():

    if "user" not in session:
        return False

    return True


# =========================
# HOME DASHBOARD
# =========================


@app.route("/")
def home():

    if not check_login():
        return redirect(url_for("login"))

    analyses = Analysis.query.filter_by(username=session["user"]).all()

    total_analyses = len(analyses)

    ats_scores = []

    for item in analyses:

        try:

            score = int("".join(filter(str.isdigit, item.ats_score)))

            ats_scores.append(score)

        except:
            pass

    if ats_scores:

        average_ats = round(sum(ats_scores) / len(ats_scores))

        best_ats = max(ats_scores)

    else:

        average_ats = 0

        best_ats = 0

    total_chats = total_analyses * 2

    if average_ats >= 85:

        resume_quality = "Excellent"

    elif average_ats >= 70:

        resume_quality = "Strong"

    elif average_ats >= 50:

        resume_quality = "Moderate"

    else:

        resume_quality = "Needs Improvement"

    recent_analysis = (
        Analysis.query.filter_by(username=session["user"])
        .order_by(Analysis.id.desc())
        .first()
    )

    return render_template(
        "dashboard.html",
        username=session["user"],
        total_analyses=total_analyses,
        average_ats=average_ats,
        best_ats=best_ats,
        total_chats=total_chats,
        resume_quality=resume_quality,
        recent_analysis=recent_analysis,
    )


# =========================
# DASHBOARD PAGE
# =========================


@app.route("/dashboard")
def dashboard():

    return home()


# =========================
# ANALYSIS PAGE
# =========================

@app.route("/analysis")
def analysis_page():

    if not check_login():
        return redirect(url_for("login"))

    analyses = Analysis.query.filter_by(
        username=session["user"]
    ).all()

    total_analyses = len(analyses)

    ats_scores = []

    for item in analyses:

        try:

            score = int(
                "".join(filter(str.isdigit, item.ats_score))
            )

            ats_scores.append(score)

        except:
            pass

    if ats_scores:

        average_ats = round(
            sum(ats_scores) / len(ats_scores)
        )

        best_ats = max(ats_scores)

    else:

        average_ats = 0

        best_ats = 0

    # =========================
    # GET LATEST ANALYSIS
    # =========================

    latest_analysis = (
        Analysis.query.filter_by(
            username=session["user"]
        )
        .order_by(Analysis.id.desc())
        .first()
    )

    # =========================
    # DEFAULT VALUES
    # =========================

    ats_health = "LOW"

    keyword_health = "LOW"

    resume_visibility = "LOW"

    recruiter_feedback = []

    improvement_checklist = []

    recruiter_ready = "NOT READY"

    detected_domain = "General"

    primary_stack = "Not Detected"

    ats_match_level = "LOW MATCH"

    # =========================
    # REAL AI LOGIC
    # =========================

    if latest_analysis:

        import re

        resume_skills = re.split(
            r'\d+\.\s*|\n|,',
            latest_analysis.top_skills
        )

        resume_skills = [
            skill.strip()
            for skill in resume_skills
            if skill.strip()
        ]

        missing_skills = re.split(
            r'\d+\.\s*|\n|,',
            latest_analysis.missing_skills
        )

        missing_skills = [
            skill.strip()
            for skill in missing_skills
            if skill.strip()
        ]
        
        # =========================
        # REAL JD vs RESUME MATCHING
        # =========================

        matched_skills = []

        for skill in resume_skills:

            for missing in missing_skills:

                if skill.lower().strip() == missing.lower().strip():

                    matched_skills.append(skill)

        if len(missing_skills) > 0:

            overall_match = int(
                (len(matched_skills) / len(missing_skills)) * 100
            )

        else:

            overall_match = 0

        # =========================
        # HEALTH STATUS
        # =========================

        if average_ats >= 80:
            ats_health = "GOOD"

        elif average_ats >= 60:
            ats_health = "MEDIUM"

        else:
            ats_health = "LOW"

        if best_ats >= 80:
            keyword_health = "HIGH"

        elif best_ats >= 60:
            keyword_health = "MEDIUM"

        else:
            keyword_health = "LOW"

        if average_ats >= 75:
            resume_visibility = "HIGH"

        else:
            resume_visibility = "MEDIUM"

        # =========================
        # RECRUITER FEEDBACK
        # =========================

        recruiter_feedback = []

        if average_ats >= 80:

            recruiter_feedback.append(
                "Strong ATS optimization detected"
            )

        else:

            recruiter_feedback.append(
                "ATS score needs improvement"
            )

        if len(missing_skills) <= 3:

            recruiter_feedback.append(
                "Good technical keyword matching"
            )

        else:

            recruiter_feedback.append(
                "Missing important JD skills"
            )

        if len(resume_skills) >= 5:

            recruiter_feedback.append(
                "Strong technical skill visibility"
            )

        # =========================
        # IMPROVEMENT CHECKLIST
        # =========================

        improvement_checklist = []

        if "github" not in latest_analysis.ai_result.lower():

            improvement_checklist.append(
                "Add GitHub Profile"
            )

        if len(missing_skills) > 0:

            improvement_checklist.append(
                "Improve missing technical skills"
            )

        improvement_checklist.append(
            "Improve project descriptions"
        )

        improvement_checklist.append(
            "Add measurable achievements"
        )

        # =========================
        # RECRUITER READY
        # =========================

        if average_ats >= 75:

            recruiter_ready = "READY"

        else:

            recruiter_ready = "NOT READY"
            
        


        # =========================
        # ATS MATCH LEVEL
        # =========================

        if best_ats >= 80:

            ats_match_level = "Strong Match"

        elif best_ats >= 60:

            ats_match_level = "Medium Match"

        else:

            ats_match_level = "Low Match"

    return render_template(
        "analysis.html",

        username=session["user"],

        total_analyses=total_analyses,

        average_ats=average_ats,

        best_ats=best_ats,
        
        matched_skills=matched_skills,
        
        missing_skills=missing_skills,
        
        overall_match=overall_match,

        ats_health=ats_health,

        keyword_health=keyword_health,

        resume_visibility=resume_visibility,

        recruiter_feedback=recruiter_feedback,

        improvement_checklist=improvement_checklist,

        recruiter_ready=recruiter_ready,

        detected_domain=detected_domain,

        primary_stack=primary_stack,

        ats_match_level=ats_match_level,
    )



# =========================
# CAREER PAGE
# =========================


@app.route("/career")
def career_page():

    if not check_login():
        return redirect(url_for("login"))

    return render_template("career.html", username=session["user"])


# =========================
# SKILLS PAGE
# =========================

@app.route("/skills")
def skills_page():

    if not check_login():
        return redirect(url_for("login"))

    latest_analysis = (
        Analysis.query.filter_by(username=session["user"])
        .order_by(Analysis.id.desc())
        .first()
    )

    if latest_analysis:

        try:
            ats_numeric = int(
                "".join(filter(str.isdigit, latest_analysis.ats_score))
            )

        except:
            ats_numeric = 0

        # =========================
        # JOB ROLES
        # =========================

        job_roles = []

        if latest_analysis.job_roles:

            lines = latest_analysis.job_roles.split("\n")

            for line in lines:

                if "-" in line:

                    role, score = line.split("-", 1)

                    score_number = "".join(
                        filter(str.isdigit, score)
                    )

                    if score_number == "":
                        score_number = "0"

                    job_roles.append({
                        "role": role.strip(),
                        "score": int(score_number)
                    })

        # =========================
        # SKILL MATCH DATA
        # =========================

                import re

        resume_skills = re.split(
            r'\d+\.\s*|\n|,',
            latest_analysis.top_skills
        )

        resume_skills = [
            skill.strip()
            for skill in resume_skills
            if skill.strip()
        ]

        jd_skills = re.split(
            r'\d+\.\s*|\n|,',
            latest_analysis.missing_skills
        )

        jd_skills = [
            skill.strip()
            for skill in jd_skills
            if skill.strip()
        ]

        matched_skills = []

        missing_skills = []

        for jd_skill in jd_skills:

            found = False

            for resume_skill in resume_skills:

                if jd_skill.lower().strip() == resume_skill.lower().strip():

                    matched_skills.append(jd_skill)

                    found = True

                    break

            if not found:

                missing_skills.append(jd_skill)

        if len(jd_skills) > 0:

            overall_match = int(
                (len(matched_skills) / len(jd_skills)) * 100
            )

        else:

            overall_match = 0

        # =========================
        # ATS KEYWORD COVERAGE
        # =========================

        if len(jd_skills) > 0:

            matched_keywords = int(
                (len(matched_skills) / len(jd_skills)) * 100
            )

        else:

            matched_keywords = 0

        missing_keywords = 100 - matched_keywords

        # =========================
        # PRIORITY SKILLS
        # =========================

        priority_skills = missing_skills[:5]
        
        # =========================
        # DYNAMIC STRONGEST AREA
        # =========================

        if len(matched_skills) >= 2:

            strongest_area = (
                matched_skills[0]
                + " & " +
                matched_skills[1]
                )

        elif len(matched_skills) == 1:

            strongest_area = matched_skills[0]

        else:

            strongest_area = "No strong matching skills found"

        # =========================
        # DYNAMIC WEAKEST AREA
        # =========================

        if len(missing_skills) >= 2:

            weakest_area = (
                missing_skills[0]
                + " & " +
                missing_skills[1]
                )

        elif len(missing_skills) == 1:

            weakest_area = missing_skills[0]

        else:

            weakest_area = "No major skill gaps"
        
        
        # =========================
        # DYNAMIC RECOMMENDED PROJECTS
        # =========================

        recommended_projects = []

        for skill in missing_skills[:3]:

            recommended_projects.append(
        f"{skill} Practice Project"
    )
        
        return render_template(
            "skills.html",
            username=session["user"],
            top_skills=latest_analysis.top_skills,
            missing_skills=latest_analysis.missing_skills,
            suggestions=latest_analysis.suggestions,
            ats_score=latest_analysis.ats_score,
            
            resume_skills=resume_skills,
            jd_skills=jd_skills,
            overall_match=overall_match,
            
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            priority_skills=priority_skills,
            strongest_area=strongest_area,
            weakest_area=weakest_area,
            recommended_projects=recommended_projects,
            job_roles=job_roles
        )

    return render_template(
        "skills.html",
        username=session["user"],
        top_skills="Upload resume first",
        missing_skills="No missing skills available",
        suggestions="Analyze a resume to get AI recommendations",
        ats_score="0",
        matched_keywords=0,
        missing_keywords=0,
        priority_skills=[],
        strongest_area="No analysis available",
        weakest_area="No analysis available",
        recommended_projects=[],
        skill_match_data=[],
        job_roles=[]
    )

# =========================
# HISTORY PAGE
# =========================

# =========================
# ATS PAGE
# =========================

@app.route("/ats")
def ats_page():

    if not check_login():
        return redirect(url_for("login"))

    latest_analysis = (
        Analysis.query.filter_by(
            username=session["user"]
        )
        .order_by(Analysis.id.desc())
        .first()
    )

    if latest_analysis:

        return render_template(
            "ats.html",
            username=session["user"],
            uploaded=True,
            filename=latest_analysis.filename,
            ats_score=latest_analysis.ats_score,
            match_percentage=latest_analysis.match_percentage,
            domain_match=latest_analysis.domain_match,
            top_skills=latest_analysis.top_skills,
            missing_skills=latest_analysis.missing_skills,
            suggestions=latest_analysis.suggestions,
            ai_result=latest_analysis.ai_result,
            resume_text=session.get("resume_text", ""),
            job_description=session.get("job_description", ""),
            fake_job_detection="Not Available",
            job_authenticity_score="0",
            scam_indicators="Not Available",
            interview_preparation="Not Available",
            learning_roadmap="Not Available",
            recruiter_recommendations="Not Available",
            job_roles=[],
            overall_match=0
        )

    return render_template(
        "ats.html",
        username=session["user"],
        uploaded=False,
        fake_job_detection="Not Available",
        job_authenticity_score="0",
        scam_indicators="Not Available",
        interview_preparation="Not Available",
        learning_roadmap="Not Available",
        recruiter_recommendations="Not Available",
        job_roles=[],
        overall_match=0
    )

@app.route("/history")
def history_page():

    if not check_login():
        return redirect(url_for("login"))

    history = (
        Analysis.query.filter_by(username=session["user"])
        .order_by(Analysis.id.desc())
        .all()
    )

    return render_template("history.html", username=session["user"], history=history)


# =========================
# SIGNUP
# =========================


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]

        email = request.form["email"]

        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already exists"

        new_user = User(username=username, email=email, password=password)

        DB.session.add(new_user)

        DB.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


# =========================
# LOGIN
# =========================


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]

        user = User.query.filter_by(
            email=email,
            password=password
        ).first()

        if user:

            session["user"] = user.username

            return redirect(url_for("home"))

        else:

            error = "Invalid email or password"

    return render_template(
        "login.html",
        error=error
    )

# =========================
# LOGOUT
# =========================


@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))


# =========================
# CAREER CHAT
# =========================


@app.route("/career-chat", methods=["POST"])
def career_chat():

    if not check_login():
        return redirect(url_for("login"))

    user_message = request.form.get("career_message")

    prompt = f"""
    You are SmartHire AI Career Coach.

    Help students with:
    - internships
    - placements
    - AI careers
    - coding roadmap
    - interview prep
    - resume advice

    USER QUESTION:
    {user_message}
    """

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        chatbot_response = response.choices[0].message.content

    except Exception as e:

        chatbot_response = f"AI Error: {str(e)}"

    return render_template(
        "career.html", username=session["user"], chatbot_response=chatbot_response
    )


# =========================
# ATS ANALYZER
# =========================


@app.route("/upload", methods=["POST"])
def upload_resume():

    if not check_login():
        return redirect(url_for("login"))

    if "resume" not in request.files:
        return redirect(url_for("ats_page"))

    file = request.files["resume"]

    if file.filename == "":
        return redirect(url_for("ats_page"))

    job_description = request.form.get("job_description")

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    file.save(filepath)

    doc = fitz.open(filepath)

    extracted_text = ""

    for page in doc:
        extracted_text += page.get_text()

    extracted_text = extracted_text[:5000]

    prompt = f"""
You are SmartHire AI.

Analyze BOTH:
1. Resume
2. Job Description

Your task is to generate recruiter-focused ATS intelligence.

IMPORTANT RULES:
- Do NOT generate random suggestions.
- Do NOT invent fake experience.
- Skills must come from resume analysis.
- Missing skills must come from JD comparison.
- Recommendations must depend on recruiter expectations.
- Roadmap must depend on missing skills.

RETURN RESPONSE EXACTLY IN THIS FORMAT:

ATS_SCORE:
Give ATS score out of 100.

MATCH_PERCENTAGE:
Give recruiter match percentage.

DOMAIN_MATCH:
Tell best matching role/domain.
JOB_READINESS_ROLES:
Generate top 3 most suitable career roles based ONLY on:
- uploaded resume
- job description
- extracted skills
- missing skills

Format:
Role Name - Score
Role Name - Score
Role Name - Score

TOP_SKILLS:
List skills detected from resume.

JD_SKILLS:
List ALL skills found in the Job Description.

MISSING_SKILLS:
List important missing skills required by JD.

LEARNING_ROADMAP:
Give roadmap based on missing skills.

RECRUITER_RECOMMENDATIONS:
Give recruiter-focused improvement suggestions.

INTERVIEW_PREPARATION:
Give interview preparation topics.
FAKE_JOB_DETECTION:
Detect whether the job description
looks suspicious, scam-like,
fake hiring,
training-fee fraud,
unrealistic salary promises
or suspicious recruiter behavior.

JOB_AUTHENTICITY_SCORE:
Give authenticity score out of 100.

SCAM_INDICATORS:
List suspicious patterns if found.

JOB DESCRIPTION:
{job_description}

RESUME:
{extracted_text}
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )

        ai_result = response.choices[0].message.content

        print("\n========== AI RESULT ==========")
        print(ai_result)
        print("========== END AI RESULT ==========\n")

        ats_score = "0"

        match_percentage = "0"

        domain_match = "Unknown"

        top_skills = "Not Available"

        missing_skills = "Not Available"

        learning_roadmap = "Not Available"

        recruiter_recommendations = "Not Available"

        interview_preparation = "Not Available"

        suggestions = "Not Available"

        fake_job_detection = "Not Available"

        job_authenticity_score = "0"

        scam_indicators = "Not Available"

                # =========================
        # DEFAULT VARIABLES
        # =========================

        roles_text = ""

        job_roles = []

        jd_skills = []

        resume_skills = []

        matched_skills = []

        missing_skill_list = []

        overall_match = 0

        try:

            if "ATS_SCORE:" in ai_result:

                ats_score = (
                    ai_result.split("ATS_SCORE:")[1]
                    .split("MATCH_PERCENTAGE:")[0]
                    .strip()
                )

            if "MATCH_PERCENTAGE:" in ai_result:

                match_percentage = (
                    ai_result.split("MATCH_PERCENTAGE:")[1]
                    .split("DOMAIN_MATCH:")[0]
                    .strip()
                )

            if "DOMAIN_MATCH:" in ai_result:

                domain_match = (
                    ai_result.split("DOMAIN_MATCH:")[1]
                    .split("JOB_READINESS_ROLES:")[0]
                    .strip()
                )

            # =========================
            # JOB READINESS ROLES
            # =========================

            job_roles = []

            if "JOB_READINESS_ROLES:" in ai_result:

                roles_text = (
                    ai_result.split("JOB_READINESS_ROLES:")[1]
                    .split("TOP_SKILLS:")[0]
                    .strip()
                )

                lines = roles_text.split("\n")

                for line in lines:

                    if "-" in line:

                        role, score = line.split("-", 1)

                        score_number = "".join(filter(str.isdigit, score))

                        if score_number == "":
                            score_number = "0"

                        job_roles.append(
                            {"role": role.strip(), "score": int(score_number)}
                        )
            if "TOP_SKILLS:" in ai_result:

                top_skills = (
                    ai_result.split("TOP_SKILLS:")[1]
                    .split("JD_SKILLS:")[0]
                    .strip()
                )

            # =========================
            # EXTRACT JD SKILLS
            # =========================

            jd_skills = []

            if "JD_SKILLS:" in ai_result:

                jd_skills_text = (
                    ai_result.split("JD_SKILLS:")[1]
                    .split("MISSING_SKILLS:")[0]
                    .strip()
                )

                jd_skills = re.split(
                    r'\d+\.\s*|\n|,',
                    jd_skills_text
                )

                jd_skills = [
                    skill.strip()
                    for skill in jd_skills
                    if skill.strip()
                ]

            if "MISSING_SKILLS:" in ai_result:

                missing_skills = (
                    ai_result.split("MISSING_SKILLS:")[1]
                    .split("LEARNING_ROADMAP:")[0]
                    .strip()
                )

            if "LEARNING_ROADMAP:" in ai_result:

                learning_roadmap = (
                    ai_result.split("LEARNING_ROADMAP:")[1]
                    .split("RECRUITER_RECOMMENDATIONS:")[0]
                    .strip()
                )

            if "RECRUITER_RECOMMENDATIONS:" in ai_result:

                recruiter_recommendations = (
                    ai_result.split("RECRUITER_RECOMMENDATIONS:")[1]
                    .split("INTERVIEW_PREPARATION:")[0]
                    .strip()
                )

            if "FAKE_JOB_DETECTION:" in ai_result:

                fake_job_detection = (
                    ai_result.split("FAKE_JOB_DETECTION:")[1]
                    .split("JOB_AUTHENTICITY_SCORE:")[0]
                    .strip()
                )

            if "JOB_AUTHENTICITY_SCORE:" in ai_result:

                job_authenticity_score = (
                    ai_result.split("JOB_AUTHENTICITY_SCORE:")[1]
                    .split("SCAM_INDICATORS:")[0]
                    .strip()
                )
            if "SCAM_INDICATORS:" in ai_result:

                scam_indicators = ai_result.split("SCAM_INDICATORS:")[1].strip()

            if "INTERVIEW_PREPARATION:" in ai_result:

                interview_preparation = ai_result.split("INTERVIEW_PREPARATION:")[1].strip()

            suggestions = recruiter_recommendations
            
            # =========================
            # SKILL MATCH LOGIC
            # =========================

            resume_skills = re.split(r'\d+\.\s*|\n|,', top_skills)

            resume_skills = [
                skill.strip()
                for skill in resume_skills
                if skill.strip()
            ]

            matched_skills = []

            missing_skill_list = []

            for skill in jd_skills:

                found = False

                for rskill in resume_skills:

                    if skill.lower().strip() == rskill.lower().strip():

                        found = True
                        break

                if found:
                    matched_skills.append(skill)

                else:
                    missing_skill_list.append(skill)

            if len(jd_skills) > 0:

                overall_match = int(
                    (len(matched_skills) / len(jd_skills)) * 100
                )

            else:

                overall_match = 0

        except:
            pass

        new_analysis = Analysis(
            username=session["user"],
            filename=file.filename,
            ats_score=ats_score,
            match_percentage=match_percentage,
            domain_match=domain_match,
            top_skills=top_skills,
            missing_skills=missing_skills,
            suggestions=suggestions,
            ai_result=ai_result,
            job_roles=roles_text,
        )

        DB.session.add(new_analysis)

        DB.session.commit()

        session["resume_text"] = extracted_text

        session["job_description"] = job_description

        session["filename"] = file.filename
        
        return render_template(
    "ats.html",
    uploaded=True,
    ats_score=ats_score,
    match_percentage=match_percentage,
    domain_match=domain_match,
    top_skills=top_skills,
    missing_skills=missing_skills,
    suggestions=suggestions,
    ai_result=ai_result,
    filename=file.filename,
    job_roles=job_roles,
    resume_skills=resume_skills,
    jd_skills=jd_skills,
    overall_match=overall_match,
    resume_text=session.get("resume_text", ""),
    job_description=session.get("job_description", ""),
    fake_job_detection=fake_job_detection,
    job_authenticity_score=job_authenticity_score,
    scam_indicators=scam_indicators,
    interview_preparation=interview_preparation,
    learning_roadmap=learning_roadmap,
    recruiter_recommendations=recruiter_recommendations
)

    except Exception as e:

        # Define variables so the HTML doesn't crash
        fake_job_detection = "Not Available"
        job_authenticity_score = "0"
        scam_indicators = "Not Available"
        interview_preparation = "Not Available"
        learning_roadmap = "Not Available"
        recruiter_recommendations = "Not Available"

        return render_template(
            "ats.html",
            uploaded=True,
            ats_score="0",
            match_percentage="0",
            domain_match="Error",
            top_skills="Not Available",
            missing_skills="Not Available",
            suggestions=f"AI Error: {str(e)}",
            ai_result=f"AI Error: {str(e)}",
            filename=file.filename,
            job_roles=[],
            # ADD THESE NEW LINES BELOW:
            resume_text=session.get("resume_text", ""),
            job_description=session.get("job_description", ""),
            fake_job_detection=fake_job_detection,
            job_authenticity_score=job_authenticity_score,
            scam_indicators=scam_indicators,
            interview_preparation=interview_preparation,
            learning_roadmap=learning_roadmap,
            recruiter_recommendations=recruiter_recommendations
        )
        

@app.route("/rebuild-resume", methods=["POST"])
def rebuild_resume():
    print("REBUILD ROUTE HIT")

    if not check_login():
        return redirect(url_for("login"))

    resume_text = session.get("resume_text", "")
    job_description = session.get("job_description", "")

    if not resume_text:

        return {
            "success": False,
            "resume": "Resume not found."
        }

    prompt = f"""
You are an ATS Resume Reconstruction Engine.

IMPORTANT RULES:

1. Analyze BOTH the Resume and Job Description.
2. Extract all important keywords and skills from the Job Description.
3. Compare Resume skills with Job Description skills.
4. Identify missing Job Description skills.
5. Rewrite the resume to maximize ATS compatibility.
6. Add relevant Job Description keywords into the Skills section.
7. Rewrite the Professional Summary using Job Description keywords.
8. Improve ATS readability and recruiter visibility.
9. Keep Education, Projects, and Experience truthful.
10. Do not invent fake companies, degrees, certifications, or projects.
11. If information is missing, return "".
12. Never return "undefined".
13. Never return "null".
14. Return VALID JSON ONLY.
15. Generate an ATS-optimized resume that closely matches the Job Description.
16. Include 8-12 professional skills by combining Resume skills and Job Description skills.
17. ALWAYS populate education from the resume.
18. ALWAYS populate projects from the resume.
19. ALWAYS populate internships from the resume.
20. Do not leave education, projects, or internships empty if they exist in the resume.
21. Rewrite the Professional Summary specifically for the Job Description.
22. Prioritize Job Description keywords throughout the resume.
23. Add missing technical skills from the Job Description into the Skills section when relevant.
24. Rephrase project descriptions to highlight skills required in the Job Description.
25. Rephrase internship descriptions to align with the Job Description.
26. Generate a recruiter-friendly ATS resume optimized for this specific role.
27. Target an ATS match score of 90% or higher.
28. Rewrite internship descriptions using keywords from the Job Description.
29. Rewrite project descriptions using keywords from the Job Description.
30. Highlight responsibilities related to operations, reporting, data collection, teamwork, and problem-solving when supported by the resume.
31. Prioritize ATS keywords from the Job Description across the Professional Summary, Skills, Internship, and Projects sections.
32. Generate content that improves ATS matching while remaining truthful to the original resume.
33. Extract all required and preferred skills from the Job Description.
34. Include relevant preferred skills in the ATS resume when they are reasonably related to the candidate's education, internship, or projects.
35. Emphasize agricultural operations, crop monitoring, greenhouse management, agricultural reporting, and data collection when supported by the resume.
36. Optimize the resume to maximize ATS keyword coverage for the target role.
37. Carefully read and understand the entire original resume before making any modifications.

38. Preserve all valuable information from the original resume, including:

* Degree Education
* Intermediate Education
* Secondary Education
* Domain Expertise
* Internships
* Projects
* Achievements

39. The original resume is the primary source of truth.

40. Compare the original resume with the Job Description and identify where the candidate's existing education, projects, internships, and skills already support the Job Description requirements.

41. Do not blindly copy Job Description keywords into the resume.

42. Only include Job Description keywords that are reasonably supported by the candidate's background, education, internship experience, project work, or domain expertise.

43. Select only the top 8-10 most relevant skills for the Skills section.

44. For fresher candidates, always preserve Degree, Intermediate, and Secondary Education details if they exist in the original resume.

45. The goal is not keyword stuffing. The goal is to create a truthful ATS-optimized resume that maximizes alignment with the Job Description while remaining realistic and recruiter-friendly.
46. If a valid LinkedIn URL is not available in the original resume, leave the LinkedIn field empty instead of generating placeholder text.
47. Remove duplicate or highly similar skills. Keep only unique and relevant skills.
48. Prioritize technical and job-related skills over generic soft skills when selecting the final 8-10 skills.
49. Limit the final Skills section to 8-10 skills only.
50. Rank skills based on relevance to the Job Description.
51. If a valid LinkedIn URL is not available in the original resume, leave the LinkedIn field empty.


JOB DESCRIPTION:

{job_description}

RESUME:

{resume_text}

Return exactly:

{{
    "contact_information": {{
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": ""
    }},
    "professional_summary": "",
    "education": [
    {{
        "degree": "",
        "institution": "",
        "duration": ""
    }}
],

"skills": [],

"domain_expertise": [],

"internships": [
    {{
        "title": "",
        "organization": "",
        "description": ""
    }}
],

"projects": [
    {{
        "title": "",
        "description": ""
    }}
],

"interests": []
}}
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )

        optimized_resume = (
            response
            .choices[0]
            .message
            .content
        )
        
        print("===== AI RESPONSE =====")
        print(optimized_resume)

        try:
            resume_data = json.loads(optimized_resume)
            
            print("========== AI JSON ==========")
            print(resume_data)
            
            experience = resume_data.get("experience", [])

            if len(experience) == 0:
                resume_data["candidate_type"] = "fresher"
            else:
                resume_data["candidate_type"] = "experienced"
            
            session["rebuilt_resume"] = resume_data

        except Exception as e:
            print("JSON ERROR:", e)
            print(optimized_resume)

            return {
                "success": False,
                "resume": f"JSON Error: {str(e)}"
            }

        return {
            "success": True,
            "resume": resume_data
        }
        
    except Exception as e:

        print("========== ERROR ==========")
        print(str(e))

        return {
            "success": False,
            "resume": f"AI Error: {str(e)}"
    }  
# =========================
# DOWNLOAD REPORT
# =========================


@app.route("/download-report")
def download_report():

    if not check_login():
        return redirect(url_for("login"))

    pdf_path = "ATS_Report.pdf"

    doc = SimpleDocTemplate(pdf_path)

    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("SmartHire AI Report", styles["Title"]))

    content.append(Spacer(1, 20))

    history = (
        Analysis.query.filter_by(username=session["user"])
        .order_by(Analysis.id.desc())
        .first()
    )

    if history:

        content.append(Paragraph(f"Resume: {history.filename}", styles["BodyText"]))

        content.append(Spacer(1, 10))

        content.append(
            Paragraph(f"ATS Score: {history.ats_score}%", styles["BodyText"])
        )

    doc.build(content)

    return send_file(pdf_path, as_attachment=True)

@app.route("/download-resume-pdf")
def download_resume_pdf():

    resume = session.get("rebuilt_resume")

    if not resume:
        return "Please rebuild resume first."

    pdf_path = "Rebuilt_Resume.pdf"

    doc = SimpleDocTemplate(pdf_path)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "ATS Optimized Resume",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 12))

    # Contact Info
    contact = resume.get("contact_information", {})

    content.append(
        Paragraph(
            f"<b>Email:</b> {contact.get('email','')}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Phone:</b> {contact.get('phone','')}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"<b>LinkedIn:</b> {contact.get('linkedin','')}",
            styles["BodyText"]
        )
    )

    content.append(Spacer(1,12))

    # Summary
    content.append(
        Paragraph(
            "<b>Professional Summary</b>",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            resume.get("professional_summary",""),
            styles["BodyText"]
        )
    )

    content.append(Spacer(1,12))

    # Skills
    content.append(
        Paragraph(
            "<b>Skills</b>",
            styles["Heading2"]
        )
    )

    for skill in resume.get("skills", []):
        content.append(
            Paragraph(
                f"• {skill}",
                styles["BodyText"]
            )
        )

    content.append(Spacer(1,12))

    # Education
    content.append(
        Paragraph(
            "<b>Education</b>",
            styles["Heading2"]
        )
    )

    for edu in resume.get("education", []):
        content.append(
            Paragraph(
                f"{edu.get('degree','')} - {edu.get('institution','')}",
                styles["BodyText"]
            )
        )
        
        content.append(Spacer(1,12))

    # Internships
    content.append(
        Paragraph(
            "<b>Internships</b>",
            styles["Heading2"]
        )
    )

    for internship in resume.get("internships", []):
        content.append(
            Paragraph(
                internship.get("title",""),
                styles["BodyText"]
            )
        )

        content.append(
            Paragraph(
                internship.get("organization",""),
                styles["BodyText"]
            )
        )

        content.append(
            Paragraph(
                internship.get("description",""),
                styles["BodyText"]
            )
        )

    content.append(Spacer(1,12))

    # Projects
    content.append(
        Paragraph(
            "<b>Projects</b>",
            styles["Heading2"]
        )
    )

    for project in resume.get("projects", []):
        content.append(
            Paragraph(
                project.get("title",""),
                styles["BodyText"]
            )
        )

        content.append(
            Paragraph(
                project.get("description",""),
                styles["BodyText"]
            )
        )

    doc.build(content)

    return send_file(
        pdf_path,
        as_attachment=True
    )


@app.route("/download-resume-docx")
def download_resume_docx():
    return "DOCX Download Coming Soon"




# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)