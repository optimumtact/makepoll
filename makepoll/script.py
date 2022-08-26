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

    votes = ["optimumtact", "The best guy ever"]
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
                    "Please rank the candidates in order you would like to see them as headadmins, highest being the one you like best, You can click on a headadmin candidates name to be taken to their forum thread for their platform.</br>  <a href=\"https://tgstation13.org/phpBB/viewtopic.php?f=38&t=9965\">You can find more instructions on voting here.</a>",
                    0,
                    NULL,
                    "optimumtact",
                    INET_ATON(127.0.0.1),
                    NULL,
                    1,
                    1,
                    0
                )
                '''
            cursor.execute(sql)
            poll_id = cursor.lastrowid
            click.echo(f"Poll id was set: {poll_id}")
            for vote in votes:
                click.echo("Inserting vote");
                qsql = f'''
                INSERT INTO poll_option (
                    pollid
                    text,
                    default_percentage_calc,
                    deleted,
                )
                VALUES (
                    {poll_id},
                    {vote},
                    1,
                    0
                )
                '''
                cursor.execute(qsql)
                click.echo(f"Inserted vote question {cursor.lastrowid}")


if __name__ == '__main__':
    cli()
