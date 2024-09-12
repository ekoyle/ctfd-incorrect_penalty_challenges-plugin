from flask import Blueprint

from CTFd.models import Awards, Challenges, Fails, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils.modes import get_model


class IncorrectPenaltyChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "incorrect_penalty"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    penalty = db.Column(db.Integer, default=0)
    minimum = db.Column(db.Integer, default=0)


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
    def apply_penalty(cls, user, team, challenge, request):
        Model = get_model()

        max_penalty = challenge.value - challenge.minimum

        failed_attempt_count = (
            Fails.query.filter(
                Fails.account_id == Model.id,
                Fails.challenge_id == challenge.id,
            )
            .distinct(Fails.provided)  # don't penalize for duplicate answers
            .with_entities(Fails.provided)
            .count()
        )

        penalty = challenge.penalty * failed_attempt_count
        if penalty > max_penalty:
            penalty = max_penalty

        penalty_award = Awards(
            user_id=user.id,
            team_id=team.id if team else None,
            name=f"Incorrect attempt penalty: {challenge.name}",
            description=f"Penalty for {failed_attempt_count} distinct incorrect responses",
            value=-penalty,
            category=challenge.category,
            icon="",
        )

        # we are depending on super().solve() to commit the transaction
        # if solve() fails for some reason, we don't want to assess the penalty
        db.session.add(penalty_award)
        return challenge

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
        data["minimum"] = challenge.minimum
        return data

    @classmethod
    def solve(cls, user, team, challenge, request):
        # keep apply_penalty() before solve()
        cls.apply_penalty(user, team, challenge, request)
        super().solve(user, team, challenge, request)


def load(app):
    upgrade(plugin_name="incorrect_penalty_challenges")
    CHALLENGE_CLASSES["incorrect_penalty"] = IncorrectPenaltyValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/incorrect_penalty_challenges/assets/"
    )
