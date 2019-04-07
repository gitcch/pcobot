import pypco
import os
import parsedatetime
from datetime import datetime
from plugins.pco import msg_attachment
import pytz

pco = pypco.PCO(os.environ["WILL_PCO_APPLICATION_KEY"], os.environ["WILL_PCO_API_SECRET"])
attachment_list = []


def get_for_date(team, date_expression):
    print('Looking up the team: ', team)
    cal = parsedatetime.Calendar()
    now = datetime.now().astimezone().astimezone(pytz.utc)
    now_hour, now_minute = now.hour, now.minute
    plan_date, parse_status = cal.parse(date_expression)
    plan_date = datetime(*plan_date[:6]).astimezone().astimezone(pytz.utc)
    is_specific = False
    start_time = datetime(month=plan_date.month, day=plan_date.day, year=plan_date.year)
    if date_expression != 'today' and (plan_date.hour != now_hour or plan_date.minute != now_minute):
        # parsedatetime by default creates a datetime matching the current hour and minute if not provided
        # is_specific is True if the parsed string contains a specific time, e.g. "Sunday at 9AM"
        is_specific = True
        start_time = datetime(month=plan_date.month,
                              day=plan_date.day,
                              year=plan_date.year,
                              hour=plan_date.hour,
                              minute=plan_date.minute)
    start_time = pytz.utc.localize(start_time)
    team_members = {
        'confirmed': [],
        'unconfirmed': [],
    }
    for t in pco.services.teams.list(where={'name': team}, include='people'):
        for member in t.rel.people.list():
            for plan_person in member.rel.plan_people.list():
                for plan_time in plan_person.rel.plan_times.list():
                    starts_at = pytz.utc.localize(datetime.strptime(plan_time.starts_at, '%Y-%m-%dT%H:%M:%SZ'))
                    hour_format = starts_at.astimezone().strftime('%I:%M%p')
                    if dates_match(starts_at, start_time, is_specific):
                        if plan_person.status in ('C', 'Confirmed'):
                            team_members['confirmed'].append((plan_person, hour_format))
                        elif plan_person.status in ('U', 'Unconfirmed'):
                            team_members['unconfirmed'].append((plan_person, hour_format))
    if is_specific:
        plan_date = plan_date.astimezone()  # Convert to local timezone
        plan_date_format = plan_date.strftime('%m-%d-%Y at %I:%M%p')
    else:
        plan_date_format = plan_date.strftime('%m-%d-%Y')
    if len(team_members['confirmed']) + len(team_members['unconfirmed']) == 0:
        msg = "Could not find any team members scheduled for that date ({}).".format(plan_date_format)
    else:
        msg = '{} team members scheduled for *{}*:'.format(team.capitalize(), plan_date_format)
        for status in ['confirmed', 'unconfirmed']:
            msg += '\n\n{}:'.format(status.capitalize())
            for plan_person_tuple in team_members[status]:
                msg += '\n- {}'.format(plan_person_tuple[0].name)
                if not is_specific:
                    msg += ' ({})'.format(plan_person_tuple[1])
    attachment_list.append(msg_attachment.
                           SlackAttachment(fallback=msg, text=msg))
    return attachment_list


def get(team):
    team = team.strip()
    print("Looking up the team: ", team)
    msg = ""
    if team:
        for t in pco.services.teams.list(where={'name': team}, include='people'):
            service = t.rel.service_type.get().id
            team_id = t.id
            msg += "*" + pco.services.service_types.get(service).name
            msg += " " + t.name + ":*"
            for id_number in t.rel.people.list():
                msg += "\n" + " ".join([pco.services.people.get(id_number.id).first_name,
                                        pco.services.people.get(id_number.id).last_name])
            attachment_list.append(msg_attachment.SlackAttachment(fallback=msg, pco='services',
                                                                  text=msg, button_text="Open in Services",
                                                                  button_url="/".join(["https://services."
                                                                                       "planningcenteronline.com/"
                                                                                       "service_types",
                                                                                       service, "teams", team_id,
                                                                                       "positions"])))
            msg = ""
    else:
        print("else")
        msg = "*Planning Center Services Teams:*"
        for team in pco.services.teams.list():
            msg += "\n" + team.name
        attachment_list.append(msg_attachment.SlackAttachment(fallback=msg, pco='services',
                                                              text=msg, button_text="Open in Services",
                                                              button_url="https://services.planning"
                                                                         "centeronline.com/teams"))

    # print("msg before assigning to attachment: ", msg)
    return attachment_list


def get_team_assignments(team):
    if team:
        for t in pco.services.teams.list(where={'name': team}, include='people'):
            for member in t.rel.people.list():
                print(pco.services.people.get(member.id).first_name)
                print(pco.services.people.get(member.id).last_name)
                for plan_people in member.rel.plan_people.list():
                    print(plan_people.team_position_name)

    else:
        print("No team given")

    return


def dates_match(date_one, date_two, is_specific):
    if is_specific:
        return date_one == date_two
    else:
        return date_one.day == date_two.day and date_one.month == date_two.month and date_one.year == date_two.year


if __name__ == '__main__':
    team = 'Band'
    print("Getting a team:")
    for x in get(team):
        print(x.slack())
    print("Getting Team Assignments:")
    get_team_assignments(team)
