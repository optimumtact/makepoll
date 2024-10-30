import csv
import random
from collections import Counter, defaultdict

import click
import pymysql
from bs4 import BeautifulSoup


# Load words from the default Debian wordlist
def load_wordlist():
    with open("/usr/share/dict/words", "r") as file:
        words = [
            line.strip() for line in file if line.strip().isalpha()
        ]  # Load only alphabetic words
    return words


# Function to generate a random 6-word phrase  ( i hope this is enough to avoid any conflicts lol)
def random_six_word_phrase():
    words = load_wordlist()  # Load the wordlist
    return " ".join(random.choice(words) for _ in range(6))  # Join 6 random words


def get_vote_options(connection, pollid):
    sql = """
SELECT id AS questionid, text AS questiontext
  FROM `poll_option`
 WHERE pollid = %s"""
    vote_options = dict()
    with connection.cursor() as cursor:
        cursor.execute(sql, (pollid))
        result = cursor.fetchall()
        for questionid, text in result:
            soup = BeautifulSoup(text, "html.parser")
            a_tag = soup.find("a")
            a_text = a_tag.get_text()
            vote_options[questionid] = a_text
    return vote_options


def get_admins_with_ban(connection):
    sql = """
        SELECT ckey, rank
          FROM `admin`
"""
    ckey_with_ban = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
        for adminckey, rank in result:
            ranklist = rank.split("+")
            if has_ban(ranklist):
                ckey_with_ban.append(adminckey)
    return ckey_with_ban


def has_ban(ranklist):
    """Returns true if the rank has ban
    we cheat here by simply checking against a hardcoded list of ranks

    Args:
        ranklist (_type_): _description_
    """
    valid_ranks = [
        "GameAdmin",
        "GameMaster",
        "TrialAdmin",
        "HeadAdmin",
        "AdminTrainer",
        "Host",
    ]
    return any(x in valid_ranks for x in ranklist)


def get_valid_ckeys(connection):
    sql = """
           SELECT ckey
             FROM (
                   SELECT SUM(delta) AS living, ckey
                     FROM `role_time_log`
                    WHERE job = "Living"
                      AND datetime > DATE('2024-05-12')
                      AND datetime < DATE('2024-08-12')
                 GROUP BY ckey
                ) AS result
            WHERE living > 400
            """
    final = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for row in cursor.fetchall():
            final.append(row[0])
    return final


def get_voter_ckeys(connection, pollid):
    sql = """
        SELECT distinct(ckey)
            FROM `poll_vote`
        WHERE pollid = %s
        """
    final = []
    with connection.cursor() as cursor:
        cursor.execute(sql, (pollid))
        result = cursor.fetchall()
        for row in result:
            final.append(row[0])
    return final


def get_vote_options_and_anonymise_plus_add_data(
    connection, pollid, ckeys_with_enough_playtime, admin_ckeys, vote_options
):
    # Create a dict that maps ckey to a random six word phrase
    ckey_to_anon = defaultdict(random_six_word_phrase)
    # Safety check for a count > number options
    anon_count = Counter()
    sql = """
        SELECT id, ckey, optionid,datetime
          FROM `poll_vote`
         WHERE pollid = %s AND deleted = 0
      ORDER BY ckey, id ASC
    """
    final = []
    max_count_should_be = 3
    # vote_options.keys().len
    bad_votes = list()
    ckeycount = Counter()
    with connection.cursor() as cursor:
        cursor.execute(sql, (pollid))
        for id, ckey, optionid, datetime in cursor.fetchall():
            anon_ckey = ckey_to_anon[ckey]
            anon_count[anon_ckey] += 1
            sortorder = anon_count[anon_ckey]
            ckeycount[ckey] += 1
            if sortorder >= max_count_should_be:
                if ckey not in bad_votes:
                    bad_votes.append(ckey)
                # click.echo(f"{sortorder}, {ckey} {anon_ckey}, {max_count_should_be}")
                # raise click.Abort()
            option_text = vote_options[optionid]
            vote_time = datetime.strftime("%Y-%m-%d")
            final.append([anon_ckey, option_text, vote_time, id, sortorder])
    for ckey in bad_votes:
        count = ckeycount[ckey]
        click.echo(f"Bad vote {ckey}, {count}")
    with open("output.csv", "w", newline="") as file:
        writer = csv.writer(file)
        for row in final:
            writer.writerow(row)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--host", prompt="Host", help="The mariadb/mysql host address")
@click.option("--user", prompt="User", help="The mariadb/mysql user name")
@click.option("--password", prompt="Password", help="The mariadb/mysql user password")
@click.option("--database", prompt="Database", help="The mariadb/mysql database")
@click.option(
    "--pollid",
    prompt="ID of poll question",
    help="The database id of the poll you want the data for (must be irv form)",
)
def process_results(host, user, password, database, pollid):
    connection = pymysql.connect(
        host=host, user=user, password=password, database=database
    )
    with connection:
        ckeys_with_enough_playtime = get_valid_ckeys(connection)
        admin_ckeys = get_admins_with_ban(connection)
        vote_options = get_vote_options(connection, pollid)
        vote_ckeys = get_voter_ckeys(connection, pollid)
        admin_vote = 0
        player_vote = 0
        filtered_player_vote = 0
        filtered_out_player = 0
        total_votes = 0
        for ckey in vote_ckeys:
            total_votes += 1
            if ckey in admin_ckeys:
                admin_vote += 1
            else:
                player_vote += 1
                if ckey in ckeys_with_enough_playtime:
                    filtered_player_vote += 1
                else:
                    filtered_out_player += 1
        # click.echo(ckeys_with_enough_playtime)
        # click.echo(admin_ckeys)
        # click.echo("vote options are")
        # click.echo(vote_options)
        click.echo(f"Admins who voted {admin_vote}")
        click.echo(f"Players who voted {player_vote}")
        click.echo(f"Players who had enough activity to qualify {filtered_player_vote}")
        click.echo(f"Players who didn't have enough activity {filtered_out_player}")
        click.echo(f"Total votes: {total_votes}")
        get_vote_options_and_anonymise_plus_add_data(
            connection, pollid, ckeys_with_enough_playtime, admin_ckeys, vote_options
        )


if __name__ == "__main__":
    cli()
