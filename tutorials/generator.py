def my_gen(count=3):
    for i in range(count):
        yield i


class Person:
    def add(self, count=1):
        self.count += count
        return self.count
    

p = Person()

setattr(p, 'count', 0)
print(p.add())
