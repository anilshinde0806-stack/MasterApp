from apps.claims.repositories.dashboard_repository import (
    JobcardPipelineRepository,
)


class JobcardPipelineService:

    def __init__(
        self,
        *,
        branch=None,
        start_date=None,
        end_date=None,
    ):
        self.branch = branch
        self.start_date = start_date
        self.end_date = end_date


    def get(self):

        branch_id = (
            self.branch.id
            if self.branch
            else None
        )

       

        return JobcardPipelineRepository.get(
                branch_id=branch_id,
                start_date=self.start_date,
                end_date=self.end_date,
        )

        return {
            "active_job_cards": 0,
            "pipeline": [],
        }