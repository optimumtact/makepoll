import pymysql
import click


@click.group()
def cli():
    pass

@cli.command()
@click.option('--host', prompt='Host', help='The mariadb/mysql host address')
@click.option('--user', prompt='User', help='The mariadb/mysql user name')
@click.option('--password', prompt='Password', help='The mariadb/mysql user password')
@click.option('--database', prompt='Database', help='The mariadb/mysql database')
def create_poll(host, user, password, database):
    """ Create the poll as required """

    votes = [
        ["Rex9001", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35753"],
        ["kieth4", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35754"],
        ["Timberpoes", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35758"],
        ["TheBibleMelts", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35760"],
        ["Kinnebian", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35767"],
        ["Tegun", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35776"],
        ["Tattle", "https://tgstation13.org/phpBB/viewtopic.php?f=38&t=35777"],
    ]
    click.echo(f"Creating your dumb poll")
    connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database)
    with connection:
        with connection.cursor() as cursor:
            sql = f'''
                INSERT INTO poll_question (
                    polltype,
                    created_datetime,
                    starttime,
                    endtime,
                    question,
                    subtitle,
                    adminonly,
                    multiplechoiceoptions,
                    createdby_ckey,
                    createdby_ip,
                    for_trialmin,
                    dontshow,
                    allow_revoting,
                    deleted
                )
                VALUES (
                    "IRV",
                    NOW(),
                    NOW(),
                    NOW() + INTERVAL 7 DAY,
                    "Headmin Election poll",
                    %s,
                    0,
                    NULL,
                    "optimumtact",
                    INET_ATON('127.0.0.1'),
                    NULL,
                    1,
                    1,
                    0
                )
                '''
            subtitle = 'Please rank the candidates in order you would like to see them as headadmins <a target="_blank" href="https://tgstation13.org/phpBB/viewtopic.php?f=38&t=9965">You can find more instructions on voting here.</a>'
            cursor.execute(sql, subtitle)
            poll_id = cursor.lastrowid
            click.echo(f"Poll id was set: {poll_id}")
            for vote in votes:
                click.echo("Inserting vote")
                qsql = f'''
                INSERT INTO poll_option (
                    pollid,
                    text,
                    default_percentage_calc,
                    deleted
                )
                VALUES (
                    {poll_id},
                    %s,
                    1,
                    0
                )
                '''
                vote_text = f"<a target=\"_blank\" href=\"{vote[1]}\">{vote[0]}</a>"
                cursor.execute(qsql, vote_text)
                click.echo(f"Inserted vote question {cursor.lastrowid}")
            connection.commit()

if __name__ == '__main__':
    cli()
