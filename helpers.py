import requests, datetime, berserk, sqlite3
from chessdotcom import ChessDotComClient
from flask import redirect, render_template, session, jsonify
from functools import wraps
from datetime import datetime


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

db = sqlite3("sqlite:///chesscheats.db")

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def getCheaterObjects(username, year, month, time_class):
    #check for the user's chess.com username, in case it differs from website username
    rows = db.execute("SELECT chess_com_username FROM users WHERE username = ?", username)
    #assign the chess.com username to a variable
    chess_com_username = rows[0]["chess_com_username"]
    #use the user's chess.com username to inquire for player games by month
    data = getPlayerGamesByMonth(chess_com_username, year, month)
    #if the value returned from our function is exception, we return a string "exception" from this function
    if data == "exception":
        return "exception"
    #otherwise we use json to parse the data
    info = data.json
    #we create two empty lists, one to hold cheaters, and one to hold opponents
    cheaters = []
    opponents = []
    #we create a list of all the games returned from our monthly player games function
    gameslib = info["games"]
    #we iterate through each game in gameslib to check each opponent's fair play status
    for game in gameslib:
        #we create an empty string called lichess active, which will hold a timestamp indicating when a fair play violater was last active on lichess
        lichessactive = ""
        lichess = False
        #if the time class of the game in question matches our search
        if game["time_class"] == time_class:
        #if the white player matched the user's username, we know that black was the opponent for this game
            if game["white"]["username"].lower() == chess_com_username.lower():
                #if the player who played as black is not yet in opponents, we add them
                if game["black"]["username"] not in opponents:
                    opponents.append(game["black"]["username"])
                    #we pass black's username, along with the year, month and user username to a function that checks if black is a cheater
                    if cheat_check(game["black"]["username"], int(year), int(month), username, time_class):
                        #we check if there is a lichess account with the same username as the opponent
                        if lichess_username_exists(game["black"]["username"], "cheat"):
                            #if so, we set lichess to True and we get a timestamp of their last active time
                            lichess = True
                            lichessactive = lichess_username_exists(game["black"]["username"], "user")
                            #otherwise we set lichess to false and lichessactive to a null value
                        else:
                            lichess = False
                            lichessactive = None
                            #we append the opponent's username, a link to the games on chess.com, their lichess status, a link to the lichess account and their last active time on lichess
                        cheaters.append(cheater(game["black"]["username"], "https://www.chess.com/games/archive/{}?opponent={}".format(chess_com_username, game["black"]["username"]), lichess, "https://lichess.org/@/{}".format(game["black"]["username"]), lichessactive))
            #otherwise white must be the opponent, so we check if they've already been appended to opponents
            elif game["white"]["username"] not in opponents:
            #if they have not yet been appended, we append them
                opponents.append(game["white"]["username"])
                #we then feed them into cheat check, to see if they are a cheater
                if cheat_check(game["white"]["username"],int(year), int(month), username, time_class):
                #we check if there is a lichess account under the same username
                    if lichess_username_exists(game["white"]["username"], "cheat"):
                        #we set lichess to true
                        lichess = True
                        #we get the date they were last active on lichess
                        lichessactive = lichess_username_exists(game["white"]["username"], "user")
                        #otherwise we set Lichess to false and lichessactive to none
                    else:
                        lichess = False
                        lichessactive = None
                    #we append the opponent's username, a link to the games on chess.com, their lichess status, a link to the lichess account and their last active time on lichess
                        cheaters.append(cheater(game["white"]["username"], "https://www.chess.com/games/archive/{}?opponent={}".format(chess_com_username, game["white"]["username"]), lichess, "https://lichess.org/@/{}".format(game["white"]["username"]), lichessactive))
    return cheaters


#checks if a specified player's account has been closed for fair play violations
def cheat_check(opponent_username, year, month, user_username, time_class):
        inquirydate = (year*100) + month
        #look up to see if the username in question is already listed as a banned player in our common database
        rows = db.execute("SELECT COUNT(*) as count FROM cheatinfo WHERE username = ?", opponent_username)
        #if there is a count of 1, this means, we know the username is already banned in the common database
        if rows[0]['count'] > 0:
            #we check if the cheater is already listed in the individual user database
            cols = db.execute("SELECT COUNT(*) as count FROM ? WHERE cheater_id = ?", user_username, opponent_username)
            #if the cheater does not exist in the user database, we insert them and return true
            if cols[0]['count'] < 1:
                db.execute("INSERT INTO ?(cheater_id, inquirydate, timeclasses) VALUES(? , ?, ?)", user_username, opponent_username, inquirydate, time_class)
                return True
            else:
                return True
        #otherwise, we need to access the chess.com client api to check their status
        else:
            #if they are not yet listed in our database, we get a bool value back from a function which inquires with the api as to the status of the players account
            return chess_com_fair_play_inquiry(opponent_username, inquirydate, user_username, time_class)

#this function takes the opponent's username, the inquiry date, the user's chess username and the selected time class
def chess_com_fair_play_inquiry(opponent_username, inquirydate, user_username, time_class):
    #we set up the chess.com client api
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    #we get the player profile of the opponent
    data = client.get_player_profile(opponent_username.lower())
    #we parse this to json
    data_json = data.json
    #if the player's account has been closed for fair play violations
    if data_json["player"]["status"] != "closed:fair_play_violations":
        return False
    else:
        #we set the values of hasavatar, haslocation and hasname to true initially
        hasavatar = True
        hasname = True
        haslocation = True
        #we get their id from the server
        playerid = int(data_json["player"]["player_id"])
        #we get their username from the server
        username = data_json["player"]["username"]
        #we try and fetch the avatar url from api.
        try:
            avatarurl = data_json["player"]["avatar"]
        #if this does not work, we set hasavatar to false and set avatar url to null value
        except:
            hasavatar = False
            avatarurl = None
        #we try to fetch the name value from the api
        try: name = data_json["player"]["name"]
        #similarly, if this raises an exception, we set has name to false and set the name value to null
        except:
            hasname = False
            name = None
        #we get the player's follower count
        followers = int(data_json["player"]["followers"])
        #we see if they have a country value set
        try:
            country = (data_json["player"]["country"])[-2:]
        #if not, we set country equal to a null value
        except:
            country = None
        #we try to fetch their location from the api
        try:
            location = data_json["player"]["location"]
        #otherwise we set location to null and the haslocation variable to false
        except:
            haslocation = False
            location = None
        #we check when they were last online
        lastonline = data_json["player"]["last_online"]
        #we check when they joiend
        joined = data_json["player"]["joined"]
        #we check if they are a streamer
        is_streamer = data_json["player"]["is_streamer"]
        #we check if there is a lichess account under the same name
        lichesslink = lichess_username_exists(opponent_username, "link")
        lichessactive = lichess_username_exists(opponent_username, "user")
        try:
            db.execute("INSERT INTO cheatinfo(playerid, username, hasavatar, avatarurl, hasname, followers, country, haslocation, location, lastonline, joined, is_streamer, name, lichesslink, lichessactive) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ? , ?, ?, ?, ?, ?)", playerid, username, hasavatar, avatarurl, hasname, followers, country, haslocation, location, lastonline, joined, is_streamer, name, lichesslink, lichessactive)
        except:
            return True
        #we check if they exist in the individual user database
        try:
            db.execute("INSERT INTO ?(cheater_id, inquirydate, timeclasses) VALUES(?, ?, ?)", user_username, opponent_username, inquirydate, time_class)
            return True
        except:
            return True

#this function checks whether a lichess useraname exists and depending on string entered either returns True or False (for cheaters) or last seen at or null for users
def lichess_username_exists(opponent_username, cheatuserlink):
    #we open the lichess token file
    f = open("lichess.token", "r")
    #we read the file and assign the value to token
    token = (f.read())
    #we strip token of any leading or trailing whitespace
    token = token.strip()
    #we start a session with the token
    session = berserk.TokenSession(token)
    #we assign this client session to lichess client
    client = berserk.Client(session)
    #if we're checking a user
    if cheatuserlink == "user":
        #we inquire as to whether the username exists
        try:
            #if it does exist, we return the time they were last seen on the site
            account = client.users.get_public_data(opponent_username)
            f.close()
            return account['seenAt']
        #if no username is found, we return a null value
        except:
            f.close()
            return None
        #if we're checking for a cheater
    elif cheatuserlink == "cheat":
        #we see if the username exists, if it does, we return True, otherwise we return false
        try:
            account = client.users.get_public_data(opponent_username)
            f.close()
            return True
        except:
            f.close()
            return False
    #if we're searching for a link, we return the link of the user
    else:
        try:
            account = client.users.get_public_data(opponent_username)
            link = "https://lichess.org/@/{}".format(opponent_username)
            f.close()
            return link
        except:
            f.close()
            return None

#returns a specified players games by month
def getPlayerGamesByMonth(chess_com_username, year, month):
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    try:
        data = client.get_player_games_by_month(chess_com_username, year, month)
    except:
        data = "exception"
    return data

#This checks if the player entered a valid username for chess.com, if they did, it returns the join data, else it returns null
def check_if_chess_username_exists(username):
    #client
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    #we try to get a response from client, if we do get a reponse, we return the value of their join timestamp
    try:
        response = client.get_player_profile(username)
        data = response.json
        joined = data['player']['joined']
        return joined
    except:
        #otherwise we return a null value
        return None

#This function creates a list of archive_entry objects to be displayed in the archives
def getArchiveObjects(id):
    rows = db.execute("SELECT username, chess_joined FROM users WHERE id = ?", id)
    #assign username value to username variable
    username = rows[0]['username']
    #assign the join date value to joined
    joined = datetime.fromtimestamp(rows[0]['chess_joined'])
    #parse for join year
    joined_year = joined.year
    #parse for join month
    joined_month = joined.month
    #assign these values to integers
    joined_month_int = int(joined_month)
    joined_year_int = int(joined_year)
    #get the current time and date
    nowtime = datetime.now()
    #parse for year and convert to int
    nyear = int(nowtime.year)
    #parse for month and convert to int
    nmonth = int(nowtime.month)
    #assign a temp value to nyear and nmonth for use in while loop
    temp_year = nyear
    temp_month = nmonth
    #create an array for dates
    archive_entries = []
    i = 0
    #we will continue the while loop until temp_year is greater than or equal to join year
    while temp_year >= joined_year_int:
        #we initialize another while loop, which will continue while temp_month is greater than or equal to 1
        while temp_month >= 1:
            #we append a formatted string to dates giving a YYYY/MM format
            inquirydate = "{}/{}".format(temp_year, temp_month)
            last_updated = nowtime
            archive_entries.append(archive_entry(inquirydate, last_updated))
            cheat_d = getCheatersArchive(username, temp_year, temp_month, "daily")
            cheat_r = getCheatersArchive(username, temp_year, temp_month, "rapid")
            cheat_bl = getCheatersArchive(username, temp_year, temp_month, "blitz")
            cheat_bu = getCheatersArchive(username, temp_year, temp_month, "bullet")
            if cheat_d:
                for cheat in cheat_d:
                    archive_entries[i].cheaters_daily.append(cheat_d)
            if cheat_r:
                for cheat in cheat_r:
                    archive_entries[i].cheaters_rapid.append(cheat_r)
            if cheat_bl:
               for cheat in cheat_bl:
                   archive_entries[i].cheaters_blitz.append(cheat_bl)
            if cheat_bu:
                for cheat in cheat_bu:
                    archive_entries[i].cheaters_bullet.append(cheat_bu)
            #we decrement the temp variable
            temp_month = temp_month - 1
            i = i + 1
            #we check for the exception of the join year (where join month may not be January)
            if temp_year == joined_year_int and temp_month == joined_month_int - 1:
                i = i + 1
                #if so, we break
                break
            #otherwise, we decrement the tempyear and reset the temp month variable to 12
        temp_year = temp_year - 1
        temp_month = 12

    return archive_entries

def getCheatersArchive(username, temp_year, temp_month, time_class):
    inquirydate = (temp_year * 100) + temp_month
    cheaters_list = ""
    try:
        rows = db.execute("SELECT cheater_id FROM ? WHERE inquirydate = ? AND timeclasses = ?", username, inquirydate, time_class)
        for row in rows:
            cheaters_list += ("" + row["cheater_id"] + " " + "\n")
        return cheaters_list
    except:
        return cheaters_list

def getTournaments(username):
    tournaments = None
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    try:
        data = client.get_player_tournaments(username.lower())
        tournaments = data.json
        return tournaments
    except:
        return tournaments

def tablifyFin(tournaments):
    newtournaments = []
    for turn in tournaments:
        if turn["status"] == "active":
            get_tag = turn["url"].split("/")
            get_wins = turn["wins"]
            get_losses = turn["losses"]
            get_draws = turn["draws"]
            get_points = turn["points_awarded"]
            get_placement = turn["placement"]
            info = getTournamentData(get_tag[len(get_tag) - 1])
            newtournaments.append(tournament(info["tournament"]["name"], info["tournament"]["settings"]["rules"],info["tournament"]["settings"]["time_class"],info["tournament"]["url"], info["tournament"]["settings"]["is_rated"], len(info["tournament"]["players"]),None, None, None, None, None, None, None, None, None, None, None, None, None, get_wins, get_draws, get_losses,get_points, get_placement))
    return newtournaments

def tablifyPro(tournaments, username):
    #create an empty list
    newtournaments = []
    #iterate through the list of tournaments we were provided
    for turn in tournaments:
        #for each tournament, check if the status is active
        if turn["status"] == "active":
            #we get a tag from the url
            get_tag = turn["url"].split("/")
            #we assign the value of this tag to a variable
            tag = get_tag[len(get_tag) - 1]
            #we get tournament info from a function
            info = getTournamentData(tag)
            #we get the current round
            current_round = info["tournament"]["current_round"]
            #we get info on the current round of the tournament from a function
            round_info = getRoundData(tag, current_round)
            newtournaments.append(tournament(info["tournament"]["name"],info["tournament"]["settings"]["rules"],info["tournament"]["settings"]["time_class"],info["tournament"]["url"], info["tournament"]["settings"]["is_rated"], len(info["tournament"]["players"]), None, None, None, info["tournament"]["settings"]["user_advance_count"], len(round_info["tournament_round"]["players"]), info["tournament"]["current_round"], 0, 0, 0, 0, False, 0, 0, 0, 0, 0, 0, 0))
            #we assign the value of temp to 1
            #we create a boolean value called breakWhile
            #breakWhile = True
            #we start a while loop to iterate through groups in the tournament
            #temp = 1
            #while breakWhile:
                #we fetch information on each group from a function
                #group_data = getGroupData(tag, current_round, temp)
                #we parse data on the players from group data
                #players = group_data["tournament_round_group"]["players"]
                #for each of the players in each group
                #for player in players:
                    #we check to see if they are the user
                    #if player["username"].lower() == username.lower():
                        #if they are, we assign the data on them to a variable
                        #myPlayerData = player
                        #if we find our user, we break the while loop
                        #breakWhile = False
                        #newtournaments.append(tournament(info["tournament"]["name"],info["tournament"]["settings"]["rules"],info["tournament"]["settings"]["time_class"],info["tournament"]["url"], info["tournament"]["settings"]["is_rated"], len(info["tournament"]["players"]), None, None, None, info["tournament"]["settings"]["user_advance_count"], len(round_info["tournament_round"]["players"]), info["tournament"]["current_round"], myPlayerData["points"], 0, 0, 0, False, 0, 0, 0, 0, 0, 0, 0))
                        #group_data.clear()
                        #temp = 1
                        #players.clear()
                        #and break from the for loop
                        #break
                #we increment the group number with each iteration
                #temp = temp + 1
    return newtournaments

def getTournamentData(tag):
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    data = client.get_tournament_details(tag)
    info = data.json
    return info

def getRoundData(tag, current_round):
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    data = client.get_tournament_round(tag, current_round)
    info = data.json
    return info

def getGroupData(tag, current_round, group):
    client = ChessDotComClient(user_agent = "My Python Application username: conorscruff; contact: conorstuart88@hotmail.com")
    data = client.get_tournament_round_group_details(tag, current_round, group)
    info = data.json
    return info

def tablifyReg(tournaments):
    newtournaments = []
    for turn in tournaments:
        get_tag = turn["url"].split("/")
        tag = get_tag[len(get_tag) - 1]
        info = getTournamentData(tag)
        newtournaments.append(tournament(info["tournament"]["name"], info["tournament"]["settings"]["rules"],info["tournament"]["settings"]["time_class"],info["tournament"]["url"], info["tournament"]["settings"]["is_rated"], len(info["tournament"]["players"]),None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None))
    return newtournaments
