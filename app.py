import os, datetime, csv, sqlite3

from flask import Flask, jsonify, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, usd, lichess_username_exists, check_if_chess_username_exists, getCheaterObjects, getArchiveObjects, getTournaments, tablifyFin, tablifyReg, tablifyPro

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = sqlite3("sqlite:///chesscheats.db")

class tournament:
    def __init__(self, name, rules, time_class, url, is_rated, total_players, min_rating, max_rating, initial_group_size, user_advance_count, remaining_players, current_round, current_score, score_to_beat, my_games_remaining, opponent_games_remaining, is_tiebreak, my_tiebreak_score, opponent_tiebreak, wins, draws, losses, points_awarded, placement):
        self.name = name
        self.rules = rules
        self.time_class = time_class
        self.url = url
        self.is_rated = is_rated
        self.total_players = total_players
        self.min_rating = min_rating
        self.max_rating = max_rating
        self.initial_group_size = initial_group_size
        self.user_advance_count = user_advance_count
        self.remaining_players = remaining_players
        self.current_round = current_round
        self.current_score = current_score
        self.score_to_beat = score_to_beat
        self.my_games_remaining = my_games_remaining
        self.opponent_games_remaining = opponent_games_remaining
        self.is_tiebreak = is_tiebreak
        self.my_tiebreak_score = my_tiebreak_score
        self.opponent_tiebreak = opponent_tiebreak
        self.wins = wins
        self.draws = draws
        self.losses = losses
        self.points_awarded = points_awarded
        self.placement = placement

class cheater:
  def __init__(self, player_id, gameurl, lichess, lichessurl, lichessactive):
    self.player_id = player_id
    self.gameurl = gameurl
    self.lichess = lichess
    self.lichessurl = lichessurl
    self.lichessactive = lichessactive

class archive_entry:
    def __init__(self, inquiry_date, lastupdated):
        self.inquiry_date = inquiry_date
        self.lastupdated = lastupdated
        self.cheaters_daily = []
        self.cheaters_rapid = []
        self.cheaters_blitz = []
        self.cheaters_bullet = []

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")

@app.route("/", methods=["POST", "GET"])
@login_required
def index():
    """main page"""
    #fetch id from session
    id = session.get("user_id")
    #We fetch username and date joined from users where id matches our session id
    rows = db.execute("SELECT username, chess_joined FROM users WHERE id = ?", id)
    #username is assigned to value username
    username = rows[0]['username']
    #time joined is parsed from the returned data
    joined = datetime.fromtimestamp(rows[0]['chess_joined'])
    #we get the year and month from the timestamp respectively
    joined_year = joined.year
    joined_month = joined.month
        #we get the current date and time
    nowtime = datetime.now()
        #we parse the year and month from this
    nyear = int(nowtime.year)
    nmonth = int(nowtime.month)
    #if we come to the page by the post method
    if request.method == "POST":
        #we get the month, year and timeclass from the inquiry form
        month = request.form.get("month")
        year = request.form.get("year")
        time_class = request.form.get("time_class")
        #Check if the inquiry year is before the year the player joined
        if int(joined_year) > int(year):
            return apology("Player had not joined chess at this time", 403)
        #Check if the inquiry year is in the future
        elif int(year) > nyear:
            return apology("Please enter a year not in the future", 403)
        #Check if the inquiry year is the current year and the month is in the future
        elif int(year) == nyear and int(month) > nmonth:
            return apology("Inquiry month in the future", 403)
        elif int(year) == int(joined_year) and int(month) < int(joined_month):
            return apology("Player had not joined chess at this time", 403)
        #cheaters should be a list of cheater objects, or a string "exception" if there is an exception due to a chess.com api failure to update at start of new month
        cheaters = getCheaterObjects(username, year, month, time_class)
        if cheaters == "exception":
            return apology("Data for this month has not yet been updated")
        return render_template("cheatinfo.html", cheaters=cheaters, year=year, month=month)
    else:
        if request.args.get("year") == None:
            syear = int(joined_year)
            smonth = int(joined_month)
            years = []
            while syear <= nyear:
                years.append(syear)
                syear = syear + 1
            return render_template("index.html", years=years, nmonth=nmonth, smonth=smonth)
        else:
            year = request.args.get("year")
            month = request.args.get("month")
            return render_template("index.html")


@app.route("/suspectedcheats", methods=["POST", "GET"])
@login_required
def suspectedcheats():
    return render_template("suspectedcheats.html")

@app.route("/tournaments", methods=["POST", "GET"])
@login_required
def tournaments():
    #if request method is post
    if request.method == "POST":
        id = session.get("user_id")
        #We fetch username and date joined from users where id matches our session id
        rows = db.execute("SELECT chess_com_username, chess_joined FROM users WHERE id = ?", id)
        username = rows[0]['chess_com_username']
        if request.form.get("tournaments") == "finished":
            tournaments = getTournaments(username)
            finished = tournaments["tournaments"]["finished"]
            finished_data = tablifyFin(finished)
            registered_data= None
            return render_template("tournaments.html", finished_data=finished_data)
        elif request.form.get("tournaments") == "in_progress":
            tournaments = getTournaments(username)
            in_progress = tournaments["tournaments"]["in_progress"]
            in_progress_data = tablifyPro(in_progress, username)
            return render_template("tournaments.html", in_progress_data=in_progress_data)
        else:
            tournaments = getTournaments(username)
            registered = tournaments["tournaments"]["registered"]
            registered_data = tablifyReg(registered)
        return render_template("tournaments.html", registered_data=registered_data)
    else:
        return render_template("tournaments.html")

@app.route("/cheatinfo", methods=["POST", "GET"])
@login_required
def cheatinfo():
    if request.method == "GET":
        return redirect("/archives")
    else:
        return render_template("cheatinfo.html")

@app.route("/archives", methods=["POST", "GET"])
@login_required
def archives():
    #get the user id from session
    id = session.get("user_id")
    #get a list of archive entries to be passed to front end
    archive_objects = getArchiveObjects(id)
    #get the username data and join date from SQL
    return render_template("archives.html", archive_objects=archive_objects)

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    """Register user"""
    if request.method == "POST":
        #if no username is filled in
        if not request.form.get("username"):
            #return an apology
            return apology("must provide username", 400)
        #if no password is filled in
        elif not request.form.get("password"):
            #return an apology
            return apology("must provide password", 400)
        #if password confirmation blank
        elif not request.form.get("confirmation"):
            #return an apology
            return apology("must provide password", 400)
        #if passwords don't match
        elif request.form.get("password") != request.form.get("confirmation"):
            #return an apology
            return apology("passwords must match", 400)
        #if no chess.com username provided
        elif not request.form.get("chesscom_username"):
            #return an apology
            return apology("please provide a chess.com or lichess username", 400)
        #or
        else:
            username = request.form.get("username")
            #check if the chess.com username entered is valid
            chess_username = request.form.get("chesscom_username")
            joined = check_if_chess_username_exists(chess_username)
            #if the function returns a null value, we print an apology
            if joined == None:
                return apology("chess.com username not found", 410)
            else:
                #if a value is entered for lichess
                if request.form.get("lichess_username"):
                    #we check if the lichess username is valid using a function in helpers
                    if lichess_username_exists(request.form.get("lichess_username"), "cheat"):
                        #if the username for lichess does exist (bool), we get the joined timestamp and assign it to a variable
                        lichess_joined = lichess_username_exists(request.form.get("lichess_username"), "user")
                        #we try to insert the values into users
                        try:
                            db.execute("INSERT INTO users(username, hash, chess_com_username, lichess_username, chess_joined, lichess_joined) VALUES(?, ?, ?, ?, ?, ?)", username, generate_password_hash(request.form.get("password")), request.form.get("chesscom_username"), request.form.get("lichess_username"), joined, lichess_joined)
                       #if an exception is raised we return an apology
                        except:
                            return apology("username already exists", 400)
                        db.execute("CREATE TABLE ? (cheater_id TEXT UNIQUE NOT NULL, inquirydate INTEGER NOT NULL, timeclasses TEXT)", username)
                else:
                    #if no lichess username exists, we insert the values into the users database without the lichess value
                    try:
                        db.execute("INSERT INTO users(username, hash, chess_com_username, lichess_username, chess_joined) VALUES(?, ?, ?, ?, ?)", username, generate_password_hash(request.form.get("password")), request.form.get("chesscom_username"), request.form.get("lichess_username"), joined)
                    #if this fails, we return an apology
                    except:
                        return apology("username already exists", 400)
                        #the user is redirected to index
                    db.execute("CREATE TABLE ? (cheater_id TEXT UNIQUE NOT NULL, inquirydate INTEGER NOT NULL, timeclasses TEXT)", username)
        return redirect("/")
    else:
        return render_template("register.html")
