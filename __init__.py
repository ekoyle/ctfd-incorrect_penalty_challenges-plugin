from flask import Blueprint

from CTFd.models import Awards, Challenges, Fails, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils.modes import get_model

import sqlalchemy


class IncorrectPenaltyChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "incorrect_penalty"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    penalty = db.Column(db.Integer, default=0)
    max_penalty = db.Column(db.Integer, default=0)


class IncorrectPenaltyValueChallenge(BaseChallenge):
    id = "incorrect_penalty"  # Unique identifier used to register challenges
    name = "incorrect_penalty"  # Name of a challenge type
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/incorrect_penalty_challenges/assets/create.html",
        "update": "/plugins/incorrect_penalty_challenges/assets/update.html",
        "view": "/plugins/incorrect_penalty_challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/incorrect_penalty_challenges/assets/create.js",
        "update": "/plugins/incorrect_penalty_challenges/assets/update.js",
        "view": "/plugins/incorrect_penalty_challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/incorrect_penalty_challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "incorrect_penalty_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = IncorrectPenaltyChallenge

    @classmethod
    def previous_attempt_count(cls, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()

        Model = get_model()
        account_id = Model.id

        return (
            Fails.query.filter(
                Fails.account_id == account_id,
                Fails.challenge_id == challenge.id,
                Fails.provided == submission
            )
            .with_entities(Fails.provided)
            .count()
        )

    @classmethod
    def get_penalty_name(cls, challenge):
        penalty_name = f"Incorrect attempt penalty: {challenge.name}"
        return penalty_name

    @classmethod
    def get_penalty(cls, challenge):
        Model = get_model()
        account_id = Model.id
        penalty_name = cls.get_penalty_name(challenge)

        penalty = challenge.penalty
        is_max = False

        # max_penalty of 0 means "unlimited"
        max_total_penalty = challenge.max_penalty
        if not max_total_penalty:
            return penalty, False

        existing_penalty = (
            Awards.query.filter(
                Awards.account_id == account_id,
                Awards.name == penalty_name,
            )
            .with_entities(
                sqlalchemy.func.sum(Awards.value)
            )
            .scalar()
        )

        if existing_penalty is None:
            existing_penalty = 0
        else:
            # We store penalties as negative awards, so negate the sum
            existing_penalty = -existing_penalty

        remaining_penalty = max_total_penalty - existing_penalty
        if penalty >= remaining_penalty:
            is_max = True
            penalty = remaining_penalty

        if penalty < 0:
            penalty = 0

        return penalty, is_max

    @classmethod
    def apply_penalty(cls, user, team, challenge, request):
        previous_attempt_count = cls.previous_attempt_count(
            challenge=challenge,
            request=request,
        )

        if previous_attempt_count > 0:
            # we tried this one already, so don't assess a penalty
            return challenge

        penalty, is_max = cls.get_penalty(challenge)

        desc = "Penalty for incorrect response"
        if is_max:
            desc += " - maximum penalty reached"

        if penalty > 0:
            penalty_award = Awards(
                user_id=user.id,
                team_id=team.id if team else None,
                name=cls.get_penalty_name(challenge),
                description=desc,
                value=-penalty,
                category=challenge.category,
                icon="",
            )

            # we are depending on super().solve() to commit the transaction if fail()
            # fails for some reason, we probably don't want to assess the penalty?
            db.session.add(penalty_award)
        return challenge

    @classmethod
    def attempt(cls, challenge, request):
        correct, display = super().attempt(challenge, request)

        previous_attempt_count = cls.previous_attempt_count(
            challenge=challenge,
            request=request,
        )

        if not correct:
            penalty, is_max = cls.get_penalty(challenge)
            if previous_attempt_count:
                display += ": already attempted"
            elif penalty:
                display += f": {penalty} point penalty assessed"
            else:
                display += ": max penalty applied"

        return correct, display

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        data = super().read(challenge)
        # challenge = cls.challenge_model.query.filter_by(id=challenge.id).first()

        data["penalty"] = challenge.penalty
        data["max_penalty"] = challenge.max_penalty
        return data

    @classmethod
    def fail(cls, user, team, challenge, request):
        # keep apply_penalty() before fail()
        cls.apply_penalty(user, team, challenge, request)
        super().fail(user, team, challenge, request)


def load(app):
    upgrade(plugin_name="incorrect_penalty_challenges")
    CHALLENGE_CLASSES["incorrect_penalty"] = IncorrectPenaltyValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/incorrect_penalty_challenges/assets/"
    )
