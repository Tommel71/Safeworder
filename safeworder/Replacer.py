import re
import pandas as pd
from os import path
from detoxify import Detoxify
from functools import lru_cache
from collections import defaultdict

ROOT = path.dirname(__file__) + "/"

class Checker:

    def __init__(self):
        self.detector = Detoxify('original')

    @lru_cache(maxsize=50)
    def calculate_scores(self, text):
        return self.detector.predict(text)


class Replacer:

    def __init__(self, file=None, tolerance = 0.5, checker=None):
        

        self.tolerances = defaultdict(lambda: tolerance)

        if file is None:
            return

        self.tolerance = tolerance
        if checker:
            self.checker = checker
        else:
            self.checker = checker()

        self.initiate_mapping(file)

    def initiate_mapping(self,file): # read the mapping file

        self.replace_dict = dict()

        if file[-4:] == "xlsx":
            self.df = pd.read_excel(file, "Sheet1")
            for col in self.df.columns:
                for el in self.df[col]:
                    if el == "":
                        continue
                    if pd.isnull(el):
                        continue

                    el = el.strip()
                    self.replace_dict[el] = col.strip()

        elif file[-4:] == "json":

            self.df = pd.read_json(file, orient="index").transpose()
            for col in self.df.columns:
                for el in self.df[col]:
                    if el == "":
                        continue
                    if pd.isnull(el):
                        continue

                    el = el.strip()
                    self.replace_dict[el] = col.strip()
        else:
            raise Exception("File type not supported")

        return

    def replace_on_index(self, text, index_to_expr): # replace the words on the indices

        if not index_to_expr:
            return text

        indices, expressions = zip(*index_to_expr.items())


        adjustment = 0

        for i in range(len(indices)):
            start = indices[i][0]
            end = indices[i][1]
            text = text[:adjustment + start] + expressions[i] + text[adjustment + end:]

            adjustment = adjustment + len(expressions[i]) - (end - start)

        return text

    def select_substitutions(self, text, index_to_expr):

        def match_all(pattern, text): #  get the indices for the matches
            nonefound = False
            i = 0
            indices = []
            while not nonefound:
                j = i
                match = pattern.search(text[i:])

                if match:
                    i += match.end() + 1
                    indices.append((j + match.start(), j + match.end()))
                else:
                    nonefound = True

            return indices

        for sensitive_expression in self.replace_dict.keys():

            if self.is_clean(text, sensitive_expression):
                continue

            # make sure it is a whole word and not something concatenated like "hellosensitive_expressionthis is me
            pattern = re.compile(f"\\b{sensitive_expression}\\b", re.IGNORECASE)
            indices_expression = match_all(pattern, text)
            index_to_expr.update({i: self.replace_dict[sensitive_expression] for i in indices_expression})

        return index_to_expr

    def clean_replacements(self, index_to_expr):


        if len(index_to_expr)<=1:
            return index_to_expr

        indices, expressions = zip(*index_to_expr.items())
        indices, expressions = zip(*sorted(zip(indices, expressions), key=lambda x: x[0][0]))  # sort them together
        indices, expressions = list(indices), list(expressions)
        index_to_expr = {i: e for i, e in zip(indices, expressions)}
        keys = list(index_to_expr.keys())

        def is_intersected(left, right):
            return left[1] > right[0]

        finished = False
        n = len(keys)
        i = 0 # index for the intervals
        while not finished:
            j = 1 # how many hops to make in the next iteration
            ontothenext = False
            while not ontothenext:
                left, right = keys[i], keys[i+j]
                if is_intersected(left, right):

                    # if two of the ranges in the keys of the dictionaries overlap, pick the longer one
                    if left[1]-left[0] >= right[1]-right[0]:
                        del index_to_expr[right]
                        j += 1
                        if i+j >= n:
                            ontothenext = True
                    else:
                        del index_to_expr[left]
                        ontothenext = True
                else:
                    ontothenext=True

            i += j

            finished = i+j >= n - 1

        return index_to_expr

    def replace(self, text):
        index_to_expr = {}
        index_to_expr = self.select_substitutions(text, index_to_expr)
        index_to_expr = self.clean_replacements(index_to_expr)
        text = self.replace_on_index(text, index_to_expr)
        return text, index_to_expr

    def is_clean(self, text, sensitive_expression):
        return True


class ObscenityReplacer(Replacer):

    def __init__(self, file=None, **kwargs):
        if file is None:
            file = ROOT + "mappings/mapping_obscenity.xlsx"
        super().__init__(file, **kwargs)


    def is_clean(self, text, expression):
        scores = self.checker.calculate_scores(text)
        return scores["obscene"] < self.tolerances[expression]


class ToxicityReplacer(Replacer):


    def __init__(self, file=None, **kwargs):
        if file is None:
            file = ROOT + "mappings/mapping_toxicity.xlsx"
        super().__init__(file, **kwargs)


    def is_clean(self, text, expression):
        scores = self.checker.calculate_scores(text)
        return scores["toxicity"] < self.tolerances[expression]

class MultiReplacer(Replacer):

    def __init__(self, replacers:list, tolerances=None):
        self.replacers = replacers
        super().__init__()
        
        if tolerances:
            for replacer in self.replacers:
                replacer.tolerances.update(tolerances)


    def select_substitutions(self, text, index_to_expr):
        for replacer in self.replacers[::-1]:
            index_to_expr = replacer.select_substitutions(text, index_to_expr)
        return index_to_expr


class NSFWReplacer(MultiReplacer):

    def __init__(self, obscenity_mapping=None, toxicity_mapping=None, checker=None, tolerances=None):
        if checker is None:
            checker = Checker()

        super().__init__([ToxicityReplacer(file=toxicity_mapping, checker=checker),
                          ObscenityReplacer(file=obscenity_mapping, checker=checker)], tolerances)


if __name__ == "__main__":
    r = NSFWReplacer(obscenity_mapping="../tests/obscenity.json")
    print(r.replace("Hey, this is a test, thisshouldbereplaced, thistoo, anotherone, fucking fuck to make it obescene and trigger"))
    r = NSFWReplacer()
    print(r.replace("   It sucks so much and it sucks even more that it improves every aspect of my day because now if i stop i know i'll just start having shitty bad days again and it'll be my dumbass lazy fault with a simple fix"))
    print(r.replace("suck"))

    r = NSFWReplacer()
    print(r.replace("You suck!"))
    print(r.replace("he was sucking lemonade through the straw"))
    tolerances_suck = {"suck": 0.98, "sucks": 0.98, "sucked": 0.98, "sucking": 0.98}
    r = NSFWReplacer(tolerances=tolerances_suck)
    print(r.replace("You suck!"))
    print(r.replace("he was sucking lemonade through the straw"))
    print(r.replace("fuck you you asshole"))
    print(r.replace("People who haven't pooped in 2019 yet, why are you still holding on to last years shit?"))