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
        with open(self.filename, 'w', encoding='utf8') as f:
            json.dump(self.answers, f, indent=' ', ensure_ascii=False)

    def answer(self, question, *variants):
        """ Return number of variant if question has answer, or none """
        if question in self.answers:
            res = self.answers[question].get('answer')
            if res:
                del self.answers[question]
            return res

        self.answers[question] = dict(
            variants=variants
        )

    def ask_human(self):
        """ Ask human all pending questions """
        for question, data in self.answers.items():
            if data.get('answer') is not None:
                continue # already answered
            answer = None
            while not answer:
                print(question)
                for i, var in enumerate(data['variants'], 1):
                    print(f'{i}) {var}')
                answer = int(input('> '))
                if not (0 < answer <= len(data['variants'])):
                    answer = None
            data['answer'] = answer


if __name__ == '__main__':
    turk = Turk()
    turk.ask_human()
    turk.save()
