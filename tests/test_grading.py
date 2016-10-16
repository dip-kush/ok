import csv
import datetime
from io import StringIO

from werkzeug.exceptions import BadRequest

from server.models import db, Backup, Group, Message, GradingTask, Score
import server.utils as utils
from server import generate
from server import constants

from tests import OkTestCase

class TestGrading(OkTestCase):
    """Tests Grading/Queue Generation."""
    def setUp(self):
        super(TestGrading, self).setUp()
        self.setup_course()

        message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}

        self.active_user_ids = [self.user1.id, self.user2.id, self.user3.id]
        self.active_staff = [self.staff1, self.staff2]
        self.active_assignments = [self.assignment, self.assignment2]

        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        # Creates 5 submissions for each assignment per user, each spaced two minutes apart

        for assign in self.active_assignments:
            time = assign.due_date - datetime.timedelta(minutes=30)
            for num in range(5):
                for user_id in self.active_user_ids:
                    num += 1
                    time += datetime.timedelta(minutes=2)
                    backup = Backup(submitter_id=user_id,
                        assignment=assign, submit=True)
                    messages = [Message(kind=k, backup=backup,
                        contents=m) for k, m in message_dict.items()]
                    backup.created = time
                    db.session.add_all(messages)
                    db.session.add(backup)
                    # Debugging print if tests fails
                    # print("User {} | Assignment {} | Submission {} | Time {}".format(
                        # user_id, assign.id, num, time))
        db.session.commit()

    # def _course_submissions_ids(self, assignment):
    #     """Return IDs of students with/out submissions & IDs of submissions."""
    #     seen = set()
    #     students, submissions, no_submissions = set(), set(), set()
    #     for student in assignment.course.participations:
    #         if student.role == constants.STUDENT_ROLE and student.user_id not in seen:
    #             group = assignment.active_user_ids(student.user_id)
    #             fs = assignment.final_submission(group)
    #             seen |= group  # Perform union of two sets
    #             if fs:
    #                 students |= group
    #                 submissions.add(fs.id)
    #             else:
    #                 no_submissions |= group
    #     return students, submissions, no_submissions

    # def test_course_submissions_ids(self):
    #     students, submissions, no_submission = self._course_submissions_ids(self.assignment)
    #     self.assertEquals(sorted(list(students)), [2, 3, 4])
    #     self.assertEquals(sorted(list(no_submission)), [5, 6])
    #     self.assertEquals(sorted(list(submissions)), [14, 15])
    #     owners_by_backup = [(i, Backup.query.get(i).owners()) for i in submissions]
    #     self.assertEquals(sorted(owners_by_backup),  [(14, {2, 3}), (15, {4})])

    # def test_course_submissions(self):
    #     students, submissions, no_submission = self._course_submissions_ids(self.assignment)
    #     self.assertEquals(sorted(list(students)), [2, 3, 4])
    #     self.assertEquals(sorted(list(no_submission)), [5, 6])
    #     self.assertEquals(sorted(list(submissions)), [14, 15])


    # def test_course_submissions_optimized(self):
    #     # Slow query should be indentical to general query (which might be fast)
    #     course_submissions = self.assignment.course_submissions()
    #     slow_course_subms = self.assignment.course_submissions_slow()

    #     course_subms_filtered = self.assignment.course_submissions(include_empty=False)
    #     assert len(course_subms_filtered) < len(course_submissions)

    #     submissions = [fs['backup']['id'] for fs in course_submissions if fs['backup']]
    #     slow_submissions = [fs['backup']['id'] for fs in slow_course_subms if fs['backup']]
    #     self.assertEquals(len(submissions), len(course_subms_filtered))
    #     self.assertEquals(len(slow_submissions), len(course_subms_filtered))
    #     print("Running with {}".format(db.engine.name))

    #     if db.engine.name == 'mysql':
    #         query = self.assignment.mysql_course_submissions_query()
    #         mysql_data = [d for d in query]
    #         self.assertEquals(len(course_submissions), len(mysql_data))

    #         has_submission = sorted(list(fs['user']['id'] for fs in course_submissions
    #                              if fs['backup']))
    #         has_submission_slow = sorted(list(fs['user']['id'] for fs in slow_course_subms
    #                                   if fs['backup']))
    #         self.assertEquals(has_submission, has_submission_slow)

    #         no_subm = sorted(list(fs['user']['id'] for fs in course_submissions
    #                              if not fs['backup']))
    #         no_subm_slow = sorted(list(fs['user']['id'] for fs in slow_course_subms
    #                                   if not fs['backup']))
    #         self.assertEquals(no_subm, no_subm_slow)

    #         backup = sorted(list(fs['backup']['id'] for fs in course_submissions
    #                              if fs['backup']))
    #         backup_slow = sorted(list(fs['backup']['id'] for fs in slow_course_subms
    #                                   if fs['backup']))

    #         self.assertEquals(backup, backup_slow)
    #     else:
    #         self.assertEquals(slow_course_subms, course_submissions)


    # def test_flag(self):
    #     submission = self.assignment.submissions(self.active_user_ids).all()[10]
    #     self.assignment.flag(submission.id, self.active_user_ids)
    #     print("Flagged submission {}".format(submission.id))

    #     students, submissions, no_submission = self._course_submissions_ids(self.assignment)
    #     self.assertEquals(sorted(list(students)), [2, 3, 4])
    #     self.assertEquals(sorted(list(no_submission)), [5, 6])
    #     self.assertEquals(sorted(list(submissions)), [submission.id, 15])
    #     owners_by_backup = [(i, Backup.query.get(i).owners()) for i in submissions]
    #     self.assertEquals(sorted(owners_by_backup),  [(submission.id, {2, 3}), (15, {4})])

    # def test_queue_generation(self):
    #     students, backups, no_submissions = self._course_submissions_ids(self.assignment)

    #     tasks = GradingTask.create_staff_tasks(backups, self.active_staff,
    #                                            self.assignment.id,
    #                                            self.assignment.course.id,
    #                                            "Composition")
    #     self.assertEquals(len(tasks), 2)
    #     self.assertEquals([t.grader.id for t in tasks], [self.staff1.id, self.staff2.id])

    #     # When only_unassigned is true, it should not add any new backups
    #     tasks = GradingTask.create_staff_tasks(backups, self.active_staff,
    #                                            self.assignment.id,
    #                                            self.assignment.course.id,
    #                                            "Composition", True)
    #     self.assertEquals(len(tasks), 0)

    # def test_score_export(self):
    #     self.login(self.staff1.email)
    #     endpoint = '/admin/course/1/assignments/1/scores'
    #     response = self.client.get(endpoint)
    #     self.assert_200(response)
    #     # No Scores
    #     self.assertEquals(response.data, b'time,is_late,email,group,sid,class_account,section,assignment_id,kind,score,message,backup_id,grader\n')

    # def test_scores_with_generate(self, generate=False):
    #     if generate:
    #         db.drop_all()
    #         db.create_all()
    #         generate.seed()
    #         self.login('okstaff@okpy.org')
    #     else:
    #         backup = Backup.query.filter_by(submitter_id=self.user1.id, submit=True).first()
    #         score = Score(backup_id=backup.id, kind="Composition", score=2.0,
    #                       message="Good work", assignment_id=self.assignment.id,
    #                       grader=self.staff1)
    #         db.session.add(score)
    #         db.session.commit()
    #         self.login(self.staff1.email)

    #     endpoint = '/admin/course/1/assignments/1/scores'
    #     response = self.client.get(endpoint)
    #     self.assert_200(response)
    #     csv_rows = list(csv.reader(StringIO(str(response.data, 'utf-8'))))

    #     scores = Score.query.filter_by(assignment_id=1).all()

    #     backup_creators = []
    #     for s in scores:
    #         backup_creators.extend(s.backup.owners())

    #     self.assertEquals(len(backup_creators), len(csv_rows) - 1)

    def test_publish_grades(self):
        points = [20.0, 2.0, 15.0, 1.0, 17.0, 0.0, 20.0, 1.0]
        scores, i, users = {}, 0, [self.user1, self.user2]
        for score_kind in ['Total', 'Composition']:
            for user in users:
                for assign in self.active_assignments:
                    backup = Backup.query.filter_by(submitter_id=user.id, submit=True).first()
                    scores = Score(backup_id=backup.id, kind=score_kind, score=points[i],
                                   message="Good work", assignment_id=assign.id,
                                   grader=self.staff1)
                    db.session.add(scores)
        db.session.commit()

        # Check that by default scores are hidden
        def check_visible_scores(assignment, hidden=(), visible=()):
            for user in users:
                self.login(user.email)
                endpoint = '/{}/'.format(assign.name)
                r = self.client.get(endpoint)
                self.assert_200(r)
                source = r.get_data().decode("utf-8")
                for score in hidden:
                    self.assertFalse("<span class='label label-primary'> {}:".format(scores) in source)
                for score in visible:
                    self.assertTrue("<span class='label label-primary'> {}:".format(scores) in source)

        # for assign in self.active_assignments:
            # check_visible_scores(assign, hidden=['Total', 'Composition'])

        # Only staff and admin can make changes
        publish_endpoint = '/admin/course/{}/assignments/{}/publish'.format(self.course.id, self.assignment.id)
        for email in [self.lab_assistant1.email, self.user1.email]:
            self.login(email)
            response = self.client.post(publish_endpoint, data={})
            self.assertStatus(response, 302)


        self.login(self.staff1.email)        
        response = self.client.post(publish_endpoint, data={})
        self.assert_200(response)
        self.assertTrue('Total' in self.assignment.published_scores)
        self.assertFalse('Composition' in self.assignment.published_scores)

        self.login(self.user1.email)
        endpoint = '/{}/'.format(self.assignment.name)
        response = self.client.get(endpoint)
        source = response.get_data().decode("utf-8")
        # print(source)
        self.assertTrue("<span class='label label-primary'> Total:" in source)
        # print("first")
        # check_visible_scores(self.assignment, ['Composition'], ['Total'])
        # print("second")
        # check_visible_scores(self.assignment2, hidden=['Total', 'Composition'])



        self.login('okadmin@okpy.org')
        response = self.client.post(publish_endpoint, data={'grades':'Total', 'hide':True})
        self.assert_200(response)
        self.assertFalse('Total' in self.assignment.published_scores)




