'''
Mechanical Turk is a simple way to add human intelligence to your programs, if you
are not able to implement good enough artificial intelligence.

First you instantiate turk with turk = Turk(). It will load
its knowledge from the memory file ('turk.json' bo default), if such exists.

Every time your program needs to make some decision, it lacks sufficient intelligence for
it will call, for example:

turk.answer('%s is name of' % name, 'man', 'woman', 'not sure')

If answer was given earlier, it will return the answer. If not - record the question, and return none.
Having none, your program should do some action for default decision. Maybe postpone doing some action
until the answer is given.

Running this module as a script (`python3 turk.py`) will load the questions and will
ask user about them. Answers of user are recorded, so next run of program that 
needs intelligence, will use answers that were given.

TODO: add command line argument to select memory file.
'''
import json

class Turk:
    """ Mechanical Turk. Used to implement decisions that require human help """

    def __init__(self, filename='turk.json'):
        self.filename = filename
        try:
            with open(filename) as f:
                self.answers = json.load(f)
        except FileNotFoundError:
            self.answers = dict()

    def save(self):
        """ Save answers data to file """

        # But preserve what was already answered there
        with open(self.filename) as f:
            old_answers = json.load(f)
        for question, data in old_answers.items():
            if data.get('answer') is not None:
                self.answers[question]['answer'] = data['answer']

        with open(self.filename, 'w', encoding='utf8') as f:
            json.dump(self.answers, f, indent=' ', ensure_ascii=False)

    def answer(self, question, *variants):
        """ Return number of variant if question has answer, or none """
        if question in self.answers:
            res = self.answers[question].get('answer')
            if res:
                self.answers[question]['used'] = True
            return res

        self.answers[question] = dict(
            variants=variants
        )

    def ask_human(self):
        """ Ask human all pending questions """
        to_ask = [i for i in self.answers.items() if i[1].get('answer') is None]
        for i, (question, data) in enumerate(to_ask, 1):
            answer = None
            while not answer:
                print(f'\n\n{i}/{len(to_ask)}: ', question)
                for i, var in enumerate(data['variants'], 1):
                    print(f'{i}) {var}')
                try:
                    answer = int(input('> '))
                    if not (0 < answer <= len(data['variants'])):
                        answer = None
                except ValueError:
                    answer = None
            data['answer'] = answer


if __name__ == '__main__':
    turk = Turk()
    try:
        turk.ask_human()
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    turk.save()
