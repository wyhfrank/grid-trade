import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class DBManagerBase:
    pass
    # def create_order(self, **kwargs):
    #     raise NotImplementedError()

    # def update_order(self, order_id, **kwargs):
    #     raise NotImplementedError()


class FireStoreManager(DBManagerBase):
    def __init__(self, config_file="configs/serviceAccountKey.json"):
        if not os.path.exists(config_file):
            raise ValueError(f"Config file not exist: {config_file}")
        cred = credentials.Certificate(config_file)
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.runner_ref = None
    
    @property
    def base_ref(self):
        return self.runner_ref if self.runner_ref else self.db
    
    def create_and_use_runner(self, runner_data):
        runner_ref = self.db.collection(u'runners').document(runner_data['uid'])
        runner_ref.set(runner_data)
        self.runner_ref = runner_ref
        return runner_ref

    def update_runner(self, runner_id, runner_data):
        # docs = self.db.collection(u'runners').where(u'uid', u'==', runner_id).stream()
        # for doc in docs:
            # doc.reference.update(runner_data)
        ref = self.get_runner(runner_id=runner_id)
        if ref:
            ref.update(runner_data)
    
    def get_runner(self, runner_id):
        runner_ref = self.db.collection(u'runners').document(runner_id)
        # runner_ref = None
        # if len(docs) > 0:
            # runner_ref = docs[0].reference
        return runner_ref
        
    def create_order(self, order_dict):
        order_ref = self.base_ref.collection(u'orders').document()
        order_ref.set(order_dict)

    def update_order(self, order_id, order_data):
        docs = self.base_ref.collection(u'orders').where(u'order_id', u'==', order_id).stream()
        for doc in docs:
            doc.reference.update(order_data)

    def delete_order(self, order_id):
        docs = self.base_ref.collection(u'orders').where(u'order_id', u'==', order_id).stream()
        for doc in docs:
            doc.reference.delete()

    def get_orders(self, order_ids=None):
        if order_ids:
            docs = self.base_ref.collection(u'orders').where(u'order_id', u'in', order_ids).stream()
        else:
            docs = self.base_ref.collection(u'orders').stream()
        return docs

    ###################
    # Tests and Debugs
    @classmethod
    def _delete_all_docs(cls, base, name):
        """ CARE: delete all the doc with `name` under collection `base`. Mainly for test purpose. """
        docs = base.collection(name).stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        print(f"Deleted {count} {name}s.")

    def _delete_all_orders(self):
        """ CARE: delete all the `order` data in collection. Mainly for test purpose. """
        self._delete_all_docs(self.base_ref, u'orders')

    def _delete_all_runners(self):
        """ CARE: delete all the `runner` data in collection. Mainly for test purpose. """
        self._delete_all_docs(self.db, u'runners')

    def _test_read_order(self):
        for doc in self.get_orders():
            print(f'{doc.id} => {doc.to_dict()}')

    def _test_add_order(self):
        data = {
            'order_id': 1000,
            'status': 'Created',
        }
        self.create_order(data)
    
    def _test_update_order(self):
        order_id = 1000
        data = {'status': 'Updated', 'new_field': '1'}
        self.update_order(order_id=order_id, **data)

    def _test_create_runner(self):
        data = {
            'uid': 'uid1',
            'name': 'runner 1',
            'param': {
                'p1': 'v1',
                'p2': 'v2',
            }
        }
        return self.create_and_use_runner(data)

    def _test_update_runner(self):
        uid = 'uid1'
        data = {
            'param': {
                'p1': 'v1_new',
                'p3': 'v3',
            }
        }
        return self.update_runner(runner_id=uid, **data)
    
    def _test_default_dict(self):
        from collections import defaultdict
        
        runner_data = {
            'f1': defaultdict(int)
        }
        runner_data['f1']['buy'] += 1
        print(runner_data)
        runner_ref = self.db.collection(u'tests').document()
        runner_ref.set(runner_data)



def test():
    m = FireStoreManager()
    m._test_add_order()
    m._test_update_order()
    m._test_read_order()    
    m._delete_all_orders()

    # m.delete_order(order_id=1000)

def test_runner():
    m = FireStoreManager()
    # m._test_create_runner()
    # m._test_add_order()
    # m._test_update_order()
    # m._delete_all_orders()
    # m._delete_all_runners()

    m._test_create_runner()
    import time
    time.sleep(3)
    m._test_update_runner()

def test_default_dict():
    m = FireStoreManager()
    m._test_default_dict()


if __name__ == "__main__":
    # test()
    # test_runner()
    test_default_dict()
