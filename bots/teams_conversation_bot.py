# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from jenkinsapi.jenkins import Jenkins
import jenkins
import requests
import time
from typing import List
from botbuilder.core import CardFactory, TurnContext, MessageFactory
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import CardAction, HeroCard, Mention, ConversationParameters
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount
from botbuilder.schema._connector_client_enums import ActionTypes


class TeamsConversationBot(TeamsActivityHandler):

    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password

    async def on_message_activity(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip()

        if "Jenkins Job" in text:
            await self._message_all_members(turn_context)
            return

        if "Deploy" in text:
            await self._send_jenkins_job_card(turn_context, False)
            return

        if "DRS" in text:
            await self._confirmDRS(turn_context)
            return

        if "RollBack" in text:
            await self._rollback(turn_context)
            return

        if "TestWebhook" in text:
            await self._run_jenkins_job(turn_context)
            return

        if "TestPipeline" in text:
            await self._run_jenkins_job(turn_context)
            return

        await self._send_card(turn_context, False)
        return

    async def _mention_activity(self, turn_context: TurnContext):
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{turn_context.activity.from_property.name}</at>",
            type="mention",
        )

        reply_activity = MessageFactory.text(f"Hello {mention.text}")
        reply_activity.entities = [Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity)

    async def _send_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Deploy", text="Deploy", value="Deploy"
            ),
            CardAction(
                type=ActionTypes.im_back, title="DRS", text="DRS", value="DRS"
            ),
            CardAction(
                type=ActionTypes.im_back, title="RollBack", text="RollBack", value="RollBack"
            ),
            CardAction(
                type=ActionTypes.im_back, title="Prueba", text="Prueba", value="Prueba"
            ),
        ]

        await self._send_item_card(turn_context, buttons)

    async def _send_item_card(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Deploy, DRS, Rollback o Pruebas?", text="Elija", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _get_member(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
            else:
                raise
        else:
            await turn_context.send_activity(f"You are: {member.name}")


# SELECT ITEM TO DEPLOY


    async def _send_jenkins_job_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="TestPipeline", text="TestPipeline", value="TestPipeline"
            ),
            CardAction(
                type=ActionTypes.im_back, title="TestWebhook", text="TestWebhook", value="TestWebhook"
            ),
        ]

        await self._select_jenkins_job(turn_context, buttons)

    async def _select_jenkins_job(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Select item to deploy", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# SEND PROACTIVE MESSAGES IN ONE TO ONE CHANNELS

    async def _message_all_members(self, turn_context: TurnContext):
        # aquí se podría poner un notify members en el crq, indicando aquellas personas que deben ser notificiadas
        # en los canales personales
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        userAllowed = "Maria Garagorry Guerra"

        for member in team_members:
            if member.name == userAllowed:
                conversation_reference = TurnContext.get_conversation_reference(
                    turn_context.activity
                )

                conversation_parameters = ConversationParameters(
                    is_group=False,
                    bot=turn_context.activity.recipient,
                    members=[member],
                    tenant_id=turn_context.activity.conversation.tenant_id,
                )

                async def get_ref(tc1):
                    conversation_reference_inner = TurnContext.get_conversation_reference(
                        tc1.activity
                    )
                    return await tc1.adapter.continue_conversation(
                        conversation_reference_inner, send_message, self._app_id
                    )

                async def send_message(tc2: TurnContext):
                    return await tc2.send_activity(
                        f"{member.name}. You've got a new notification in the Deployment Channel."
                    )  # pylint: disable = cell-var-from-loop

                await turn_context.adapter.create_conversation(
                    conversation_reference, get_ref, conversation_parameters
                )


# necesito el get paged memebers para ejecutar la funcion de message members

    async def _get_paged_members(
        self, turn_context: TurnContext
    ) -> List[TeamsChannelAccount]:
        paged_members = []
        continuation_token = None

        while True:
            current_page = await TeamsInfo.get_paged_members(
                turn_context, continuation_token, 100
            )
            continuation_token = current_page.continuation_token
            paged_members.extend(current_page.members)

            if continuation_token is None:
                break

        return paged_members

# CHECK WHETHER THE USER HAS PERMISSIONS TO EXECUTE OR NOT

    async def _check_permissions(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        # este nombre es el que envia el CRQ
        userAllowed = "Maria Garagorry Guerra"
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
            else:
                raise
        else:
            if member.name != userAllowed:
                await turn_context.send_activity(f"Denied. You are not {userAllowed}, you're not allowed to perform this action")
                await self.deny_permission(turn_context)
            else:
                await turn_context.send_activity(f"You are indeed : {member.name}")
                await self._send_item_card(turn_context)


# DEPLOYMENT ITEMS BLOCK


    async def _run_jenkins_job(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        deployItem = turn_context.activity.text.strip()

        jenkinsUrl = "http://localhost:8080"
        userToken = ""
        userName = ""
        jobName = turn_context.activity.text.strip()
        auth = ("", "")
        j = jenkins.Jenkins(jenkinsUrl, username=userName, password=userToken)

        job = requests.get(
            "{0:s}/job/{1:s}/api/json".format(
                jenkinsUrl,
                jobName,
            ),
            auth=auth,
        ).json()

        next_build_number = job['nextBuildNumber']

        next_build_url = "{0:s}/job/{1:s}/{2:d}/api/json".format(
            jenkinsUrl,
            jobName,
            next_build_number,
        )

        print("Triggering build: {0:s} #{1:d}".format(jobName,
                                                      next_build_number,
                                                      ))

        response = j.build_job(jobName)

        build_status = requests.get("{0:s}/job/{1:s}/lastBuild/api/xml?xpath=/*/result".format(
            jenkinsUrl, jobName), auth=auth)

        await turn_context.send_activity(
            MessageFactory.text(
                f"The item {deployItem} will be deployed, on build number #{next_build_number}")
        )
        await turn_context.send_activity(f"Jenkins Job: {jobName} finished with status: {build_status.text}")
        await self._message_all_members(turn_context)

        buildResult = str(build_status.text).lower()
        buildSuccess = str("success")

        if buildResult == buildSuccess:
            await turn_context.send_activity("Se confirma inicion de DRS? Escribir SI o NO")
            await self._confirmDRS(turn_context)
        else:
            await self._rollback(turn_context)

    async def _confirmDRS(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        confirmation = turn_context.activity.text.strip()
        await turn_context.send_activity("Se confirma inicion de DRS")

    async def _rollback(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        confirmation = turn_context.activity.text.strip().lower()
        if confirmation == "si":
            await turn_context.send_activity("Se confirma inicion de Rollback")
        else:
            await turn_context.send_activity("Qué desea usted hacer? ")

    # async def _deploy_job(self, turn_context: TurnContext):

    #     jenkinsUrl = "http://localhost:8080"
    #     userToken = "112e83c712adbf2bbd9c77b79980230759"
    #     userName = "rosina"
    #     jobName = self.on_message_activity(turn_context)
    #     auth = ("rosina", "112e83c712adbf2bbd9c77b79980230759")
    #     j = jenkins.Jenkins(jenkinsUrl, username=userName, password=userToken)

    #     job = requests.get(
    #         "{0:s}/job/{1:s}/api/json".format(
    #             jenkinsUrl,
    #             jobName,
    #         ),
    #         auth=auth,
    #     ).json()

    #     next_build_number = job['nextBuildNumber']

    #     next_build_url = "{0:s}/job/{1:s}/{2:d}/api/json".format(
    #         jenkinsUrl,
    #         jobName,
    #         next_build_number,
    #     )

    #     print("Triggering build: {0:s} #{1:d}".format(jobName,
    #                                                   next_build_number,
    #                                                   ))

    #     response = j.build_job(jobName)

    #     build_status = requests.get("{0:s}/job/{1:s}/lastBuild/api/xml?xpath=/*/result".format(
    #         jenkinsUrl, jobName), auth=auth)

    #     await turn_context.send_activity(f"Jenkins Job: {jobName} finished with status: {build_status.text}")
    #     await self._message_all_members(turn_context)
