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

        if "AUTH-user" in text:
            await self._check_permissions(turn_context)
            return

        if "Deploy" in text:
            await self._send_jenkins_job_card(turn_context, False)
            return

        if "DRS-Proceed" in text:
            await self._message_all_members_DRS(turn_context)
            await self._confirmDRS(turn_context)
            await self._send_card_T_RB(turn_context, False)
            return

        if "TESTS-Proceed" in text:
            await self._message_all_members_TESTS(turn_context)
            await self._confirmTests(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "RB-Proceed" in text:
            await self._rollback(turn_context)
            await self._message_all_members_ROLLBACK(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "DP-Finish" in text:
            await self._finish_deployment(turn_context)
            await self._message_all_members_FINISH(turn_context)
            return

        if "TestWebhook" in text:
            await self._run_jenkins_job(turn_context)
            return

        if "TestPipeline" in text:
            await self._run_jenkins_job(turn_context)
            return

        await self._send_permissions_card(turn_context, False)
        return

# CHECK PERMISSIONS CARD

    async def _send_permissions_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Verificar Identidad", text="Check", value="AUTH-user"
            ),
        ]

        await self._send_permissions_select_card(turn_context, buttons)

    async def _send_permissions_select_card(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Chequea tus permisos", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# DEPLOY CARD

    async def _send_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Deploy", text="Deploy", value="Deploy"
            ),
        ]

        await self._send_item_card(turn_context, buttons)

    async def _send_item_card(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Deploy", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# JENKINS JOB CARD

    async def _send_jenkins_job_card(self, turn_context: TurnContext, isUpdate):
        # aqui en buttons se debe agregar los nombres de los jobs
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
            title="Seleccione el item a deployar", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# NOTIFY UN P2B ABOUT JENKINS JOB FINISH BUILDING

    async def _message_all_members_Jenkins_Job(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        for member in team_members:
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
                    f"{member.name}. Se termino el Jenkins Job, verifique estado en canal."
                )  # pylint: disable = cell-var-from-loop
            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

    async def _message_all_members_TESTS(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        for member in team_members:
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
                    f"{member.name}. Se inician las pruebas."
                )  # pylint: disable = cell-var-from-loop
            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

    async def _message_all_members_DRS(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        for member in team_members:
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
                    f"{member.name}. Inicio DRS."
                )  # pylint: disable = cell-var-from-loop
            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

    async def _message_all_members_ROLLBACK(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        for member in team_members:
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
                    f"{member.name}. Inicio de Rollback."
                )  # pylint: disable = cell-var-from-loop
            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

    async def _message_all_members_FINISH(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        # aqui deberia ir el nombre de la persona que envío el CRQ
        # pendiente ver con Facu como sería
        for member in team_members:
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
                    f"{member.name}. Finaliza deploy."
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
                await turn_context.send_activity(f"No permitido, usted es {member.name} no es {userAllowed}")
            else:
                await turn_context.send_activity(f"Usted es {userAllowed}, puede proseguir")
                await self._send_jenkins_job_card(turn_context, False)

# DEPLOYMENT ITEMS BLOCK

    async def _run_jenkins_job(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        deployItem = turn_context.activity.text.strip()

        jenkinsUrl = "http://localhost:8080"
        userToken = ""
        userName = ""
        auth = ("", "")
        jobName = turn_context.activity.text.strip()
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
        response = j.build_job(jobName)

        build_status = requests.get("{0:s}/job/{1:s}/lastBuild/api/xml?xpath=/*/result".format(
            jenkinsUrl, jobName), auth=auth)

        await turn_context.send_activity(
            MessageFactory.text(
                f"El job {deployItem} será deployado, build #{next_build_number}")
        )
        await turn_context.send_activity(f"Jenkins Job: {jobName} finalizó con estado de : {build_status.text}")
        await self._message_all_members_Jenkins_Job(turn_context)
        await self._send_card_DRS_RB(turn_context, False)

# DRS OR ROLLBACK CARD

    async def _send_card_DRS_RB(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="DRS", text="DRS", value="DRS-Proceed"
            ),
            CardAction(
                type=ActionTypes.im_back, title="RollBack", text="RollBack", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_DRS_RB(turn_context, buttons)

    async def _send_select_card_DRS_RB(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Continuar con DRS o RollBack?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _confirmDRS(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        confirmation = turn_context.activity.text.strip()
        await turn_context.send_activity("Se confirma inicio de DRS")

# TESTS OR ROLLBACK CARD

    async def _send_card_T_RB(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Tests", text="Tests", value="TESTS-Proceed"
            ),
            CardAction(
                type=ActionTypes.im_back, title="RollBack", text="RollBack", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_T_RB(turn_context, buttons)

    async def _send_select_card_T_RB(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Continuar con Tests o RollBack?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _confirmTests(self, turn_context: TurnContext):
        await turn_context.send_activity("Se confirma inicio de Pruebas")

    async def _rollback(self, turn_context: TurnContext):
        await turn_context.send_activity("Se confirma inicio de Rollback")

# FINISH DEPLOYMENT CARD

    async def _send_card_FINISH(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Finalizar", text="Finalizar", value="DP-Finish"
            ),
        ]

        await self._send_select_card_FINISH(turn_context, buttons)

    async def _send_select_card_FINISH(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Finalizar deployment?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _confirmDRS(self, turn_context: TurnContext):
        await turn_context.send_activity("Se confirma inicio de DRS")

    async def _finish_deployment(self, turn_context: TurnContext):
        await turn_context.send_activity("Se finaliza el deployment")
