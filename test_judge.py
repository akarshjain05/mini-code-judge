import sys
import os
from app.core.database import SessionLocal, Base, engine
from app.models.submission import Submission
from app.models.problem import Problem, TestCase
from app.models.user import User
from app.worker.judge import judge_submission
from app.core.security import get_password_hash

def test():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create user
    u = db.query(User).filter_by(username="testuser").first()
    if not u:
        u = User(username="testuser", email="test@test.com", hashed_password=get_password_hash("pass"), is_verified=True)
        db.add(u)
        db.commit()

    # Create problem
    p = db.query(Problem).filter_by(title="Test Problem").first()
    if not p:
        p = Problem(title="Test Problem", description="Add two numbers", difficulty="easy", author_id=u.id)
        db.add(p)
        db.commit()
        
        tc = TestCase(problem_id=p.id, stdin="1 2\n", expected="3\n", is_sample=True, is_hidden=False)
        db.add(tc)
        db.commit()

    # Create submission
    code = """
import sys
for line in sys.stdin:
    a, b = map(int, line.split())
    print(a + b)
"""
    sub = Submission(user_id=u.id, problem_id=p.id, language="python", code=code, status="pending")
    db.add(sub)
    db.commit()
    sub_id = sub.id
    
    print(f"Testing submission {sub_id} with python")
    judge_submission(sub_id)
    
    db.refresh(sub)
    print(f"Verdict: {sub.verdict}, Status: {sub.status}, Output: {sub.error_output}")
    
    # C++ Test
    code_cpp = """
#include <iostream>
using namespace std;
int main() {
    int a, b;
    while(cin >> a >> b) {
        cout << a + b << endl;
    }
    return 0;
}
"""
    sub2 = Submission(user_id=u.id, problem_id=p.id, language="cpp", code=code_cpp, status="pending")
    db.add(sub2)
    db.commit()
    sub2_id = sub2.id

    print(f"Testing submission {sub2_id} with C++")
    judge_submission(sub2_id)
    
    db.refresh(sub2)
    print(f"Verdict: {sub2.verdict}, Status: {sub2.status}, Output: {sub2.error_output}")

    db.close()

if __name__ == "__main__":
    test()
