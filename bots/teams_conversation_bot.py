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

        if "CRQ" in text:
            await self._get_crq_Number(turn_context)
            await self._run_jenkins_job(turn_context)
            return

        if "TESTS-Proceed" in text:
            await self._message_all_members_TESTS(turn_context)
            await self._confirmTests(turn_context)
            await self._send_card_DRS_RB(turn_context, False)
            return

        if "DRS-Proceed" in text:
            await self._message_all_members_DRS(turn_context)
            await self._confirmDRS(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "RB-Proceed" in text:
            await self._confirmRollback(turn_context)
            await self._message_all_members_ROLLBACK(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "DP-Finish" in text:
            await self._confirmFinish(turn_context)
            await self._message_all_members_FINISH(turn_context)
            return

        await self._send_permissions_card(turn_context, False)
        return


# CHEQUEAR PERMISOS
# esta sección tiene una función de apoyo, que es la que genera el userAllowed


    async def _check_permissions(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        # este nombre es el que envia el CRQ
        userAllowed = await self._get_users_allowed(turn_context)

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
                await self._ask_user_for_CRQ(turn_context)

# genero la función auxiliar para tomar los usuarios con permisos

    async def _get_users_allowed(self, turn_context: TurnContext):
        userAllowed = 'Maria Garagorry Guerra'
        return userAllowed

# SOLICITO CRQ

    async def _ask_user_for_CRQ(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_CRQ = MessageFactory.text(
            f"{mention.text} Ingrese la CRQ")
        reply_activity_CRQ.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_CRQ)

# DEPLOYMENT ITEMS BLOCK
# esta seccion tiene funciones de apoyo que dan la carpeta del job, y el jobname, la crq se toma del input del usuario

    async def _run_jenkins_job(self, turn_context: TurnContext):
        crqNumber = await self._get_crq_Number(turn_context)
        jobFolder = await self._get_job_Folder(turn_context)
        jobName = await self._get_job_Name(turn_context)
        userName = ''
        userToken = ''
        jenkinsUrl = 'https://jenkins.dev.wallet.prismamp.com'
        auth = (userName, userToken)
        crqCheck = ""
        job = requests.get(
            "{0:s}/job/{1:s}/job/{2:s}/api/json".format(
                jenkinsUrl,
                jobFolder,
                jobName,
            ),
            auth=auth,
        ).json()['lastBuild']

        lastBuildNumber = job['number']

        while crqCheck != crqNumber:

            buildNumber = str(lastBuildNumber)

            consoleJobs = requests.get(
                "{0:s}/job/{1:s}/job/{2:s}/{3:s}/api/json".format(
                    jenkinsUrl,
                    jobFolder,
                    jobName,
                    buildNumber,
                ),
                auth=auth,
            ).json()['actions'][0]['parameters'][4]

            crqCheck = str(consoleJobs["value"])

            if crqCheck == crqNumber:
                await turn_context.send_activity("El build numero {0:s} corresponde con la {1:s}".format(
                    buildNumber, crqCheck))
                correspondingJob = requests.get(
                    "{0:s}/job/{1:s}/job/{2:s}/{3:s}/api/json".format(
                        jenkinsUrl,
                        jobFolder,
                        jobName,
                        buildNumber,
                    ),
                    auth=auth,
                ).json()

                buildingStatus = correspondingJob['building']

                if buildingStatus == True:
                    await turn_context.send_activity('El job todavia esta ejecutandose')
                    time.sleep(10)
                    await self._run_jenkins_job(turn_context)

                if buildingStatus == False:
                    resultStatus = correspondingJob['result']
                    await turn_context.send_activity('El job {0:s}, build #{1:s}, correspondiente a la {2:s} termino con estado de: {3:s}'.format(
                        jobName, buildNumber, crqNumber, resultStatus))
                    await self._send_card_T_RB(turn_context, False)
                    # aqui deberiamos mandarle la notificacion a todos los usuarios

            else:
                print("La CRQ del build #{0:s} no se condice con la CRQ ingresada({1:s}), se continua chequeando".format(
                    buildNumber, crqNumber))
                lastBuildNumber = (lastBuildNumber - 1)

   # genero las variables basicas para el bloque de jenkins job
    async def _get_crq_Number(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        crq = turn_context.activity.text.strip()
        return crq

    async def _get_job_Folder(self, turn_context: TurnContext):
        jobFolder = 'TestBot'
        return jobFolder

    async def _get_job_Name(self, turn_context: TurnContext):
        jobName = 'TestSC'
        return jobName


# TODAS LAS CARDS, por orden de aparicion
# 1. CHECK PERMISSIONS CARD

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

# 2. TESTS OR ROLLBACK CARD

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

# 3. DRS OR ROLLBACK CARD

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


# 4. FINISH DEPLOYMENT CARD

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
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_DRS = MessageFactory.text(
            f"{mention.text} Se confirma inicio de DRS")
        reply_activity_DRS.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_DRS)

    async def _confirmTests(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_TESTS = MessageFactory.text(
            f"{mention.text} Se confirma inicio de Pruebas")
        reply_activity_TESTS.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_TESTS)

    async def _confirmRollback(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_RB = MessageFactory.text(
            f"{mention.text} Se confirma inicio de Rollback")
        reply_activity_RB.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_RB)

    async def _confirmFinish(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_DP = MessageFactory.text(
            f"{mention.text} Se confirma inicio de Rollback")
        reply_activity_DP.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_DP)


# TODAS LAS NOTIFICACIONES, por orden de aparicion
# en esta sección figuran las funciones de message_all (sobre estado de jenkins job, inicio de DRS, TESTS, ROLLBACK, o FINISHDP)
# esta sección tiene una funcion de apoyo, que es la que retorna los paged members

# 1. MESSAGE ALL MEMBERS JENKINS JOB STATUS

    async def _message_all_members_Jenkins_Job(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
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

# 2. MESSAGE ALL MEMBERS TESTS

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

# 3. MESSAGE ALL MEMBERS DRS

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

# 4. MESSAGE ALL MEMBERS ROLLBACK

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

# 5. MESSAGE ALL MEMBERS FINISH

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
