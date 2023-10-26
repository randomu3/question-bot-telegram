from database.models import db, User, ReferralLink, Question, Answer

def get_or_create_user(telegram_id):
    user = db.session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.session.add(user)
        db.session.commit()
    return user

def create_referral_link(user):
    referral_link = ReferralLink(user_id=user.id, link=f"askme:{user.id}")
    db.session.add(referral_link)
    db.session.commit()
    return referral_link

def get_referral_link(user):
    return ReferralLink.query.filter_by(user_id=user.id).first()

def create_question(referral_link, text, asker_id):
    question = Question(referral_link_id=referral_link.id, text=text, asker_id=asker_id)
    print(f"referral_link_id: {referral_link.id}, asker_id: {asker_id}, text: {text}")
    db.session.add(question)
    db.session.commit()
    return question

def create_answer(question, text):
    answer = Answer(question_id=question.id, text=text)
    db.session.add(answer)
    db.session.commit()
    return answer
