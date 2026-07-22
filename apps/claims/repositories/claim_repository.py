from core.models import Claim


class ClaimRepository:

    def get_by_id(self, claim_id):
        if not claim_id:
            return None

        return Claim.objects.filter(pk=claim_id).first()

    def create(self, claim_no, vehicle):
        return Claim(
            claim_no=claim_no,
            vehicle=vehicle,
        )

    def save(self, claim):
        claim.save()
        return claim
