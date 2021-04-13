# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from jenkinsapi.jenkins import Jenkins
import jenkins
import requests
import time
import json
import re
import sys
import os
import time
import re
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

        if "CRQ" in text:
            await self._get_crq_Number(turn_context)
            await self._check_permissions(turn_context)
            return

        if "T-Initial-proceed" in text:
            await self._confirmPrevious(turn_context)
            return

        if "T-Initial-OK" in text:
            await self._confirmDeploy(turn_context)
            return

        if "JOB-Status" in text:
            await self._check_jenkins_job_drs(turn_context)
            return

        if "TESTS-Proceed" in text:
          #  await self._message_all_members_TESTS(turn_context)
            await self._ask_control_confirmTests(turn_context)
            await self._send_card_post_tests(turn_context, False)
            return

        if "T-Post-OK" in text:
            await self._communicate_control_postTests_OK(turn_context)
            await self._ask_PROD(turn_context)
            return

        if "PROD-Proceed" in text:
            await self._message_all_members_Prod(turn_context)
            await self._confirmProd(turn_context)
            await self._send_card_follow_job_status_prod(turn_context, False)
            return

        if "PROD-JOB" in text:
            await self._check_jenkins_job_prod(turn_context)
            return

        if "T-Prod-OK" in text:
            await self._confirmFinish(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "RB-Proceed" in text:
            await self._confirmRollback(turn_context)
            await self._message_all_members_ROLLBACK(turn_context)
            await self._send_card_FINISH(turn_context, False)
            return

        if "DP-Finish" in text:
            await self._communicate_finish_deploy_streamer(turn_context)
            await self._message_all_members_FINISH(turn_context)
            return

        await self._ask_user_for_CRQ(turn_context)
        return


# CHEQUEAR PERMISOS
# esta secciOn tiene una función de apoyo, que es la que genera el userAllowed

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
                await turn_context.send_activity(f"Usted es el streamer {userAllowed}, puede proseguir")
                await self._send_card_TInitial_proceed(turn_context, False)

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

    async def _check_jenkins_job_drs(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        # await self._get_crq_Number(turn_context)""
        crqNumber = "CRQ000012346777744"
        jobFolder = await self._get_job_Folder(turn_context)
        jobName = await self._get_job_Name(turn_context)
        userName = ''
        userToken = ''
        jenkinsUrl = ''
        auth = (userName,userToken)
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
            ).json()['actions'][0]['parameters'][3]

            # add mention

            mention = Mention(
                mentioned=turn_context.activity.from_property,
                text=f"<at>{userAllowed}</at>",
                type="mention",
            )

            crqCheck = str(consoleJobs["value"])
            if crqCheck == crqNumber:

                reply_activity_job_status = MessageFactory.text(
                    "{0:s} El build numero {1:s} corresponde con la {2:s} en ambiente DRS".format(
                        mention.text, buildNumber, crqCheck))
                reply_activity_job_status.entities = [
                    Mention().deserialize(mention.serialize())]
                await turn_context.send_activity(reply_activity_job_status)

                buildingStatus = True

                while buildingStatus == True:
                    correspondingJob = requests.get(
                        "{0:s}/job/{1:s}/job/{2:s}/{3:s}/api/json".format(
                            jenkinsUrl,
                            jobFolder,
                            jobName,
                            buildNumber,
                        ),
                        auth=auth,
                    ).json()
                    await turn_context.send_activity('El job todavia esta ejecutandose')
                    time.sleep(10)
                    buildingStatus = correspondingJob['building']

                else:  # buildingStatus == False:
                    resultStatus = correspondingJob['result']
                    reply_activity_job_result = MessageFactory.text("{0:s} El job {1:s}, build  #{2:s}, correspondiente a la {3:s} termino con estado de: {4:s} en ambiente DRS".format(
                                                                    mention.text, jobName, buildNumber, crqNumber, resultStatus))
                    reply_activity_job_result.entities = [
                        Mention().deserialize(mention.serialize())]
                    await turn_context.send_activity(reply_activity_job_result)
                    await self._send_card_T_RB(turn_context, False)
                    # aqui deberiamos mandarle la notificacion a todos los usuarios

            else:
                print("La CRQ del build #{0:s} no se condice con la CRQ ingresada({1:s}), se continua chequeando".format(
                    buildNumber, crqNumber))
                lastBuildNumber = (lastBuildNumber - 1)

    async def _check_jenkins_job_prod(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        # await self._get_crq_Number(turn_context)""
        crqNumber = "CRQ000012346777744"
        jobFolder = await self._get_job_Folder(turn_context)
        jobName = await self._get_job_Name(turn_context)
        userName = ''
        userToken = ''
        jenkinsUrl = ''
        auth = ('userName', 'userToken')
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
            ).json()['actions'][0]['parameters'][3]

            # add mention

            mention = Mention(
                mentioned=turn_context.activity.from_property,
                text=f"<at>{userAllowed}</at>",
                type="mention",
            )

            crqCheck = str(consoleJobs["value"])
            if crqCheck == crqNumber:

                reply_activity_job_status = MessageFactory.text(
                    "{0:s} El build numero {1:s} corresponde con la {2:s} en ambiente de PROD".format(
                        mention.text, buildNumber, crqCheck))
                reply_activity_job_status.entities = [
                    Mention().deserialize(mention.serialize())]
                await turn_context.send_activity(reply_activity_job_status)

                buildingStatus = True

                while buildingStatus == True:
                    correspondingJob = requests.get(
                        "{0:s}/job/{1:s}/job/{2:s}/{3:s}/api/json".format(
                            jenkinsUrl,
                            jobFolder,
                            jobName,
                            buildNumber,
                        ),
                        auth=auth,
                    ).json()
                    await turn_context.send_activity('El job todavia esta ejecutandose')
                    time.sleep(10)
                    buildingStatus = correspondingJob['building']

                else:  # buildingStatus == False:
                    resultStatus = correspondingJob['result']
                    reply_activity_job_result_prod = MessageFactory.text("{0:s} El job {1:s}, build  #{2:s}, correspondiente a la {3:s} termino con estado de: {4:s} en ambiente de PROD".format(
                        mention.text, jobName, buildNumber, crqNumber, resultStatus))
                    reply_activity_job_result_prod.entities = [
                        Mention().deserialize(mention.serialize())]
                    await turn_context.send_activity(reply_activity_job_result_prod)
                    await self._ask_control_confirmProdTests(turn_context)
                    await self._send_card_post_tests_prod(turn_context, False)
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
        jobName = 'lalala'
        return jobName


# TODAS LAS CARDS, por orden de aparicion
# 1. CHECK PERMISSIONS CARD


# 1. PERMISSIONS CHECKING

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


# 2. ASK FOR INITIAL TESTS

    async def _send_card_TInitial_proceed(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Solicitar Pruebas Inciales", text="Solicitar Pruebas Inciales", value="T-Initial-proceed"
            ),
        ]

        await self._send_select_card_TInitial_proceed(turn_context, buttons)

    async def _send_select_card_TInitial_proceed(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Solicitar Pruebas Iniciales", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 3. CONFIRM INITIAL TESTS OK

    async def _send_card_confirm_TInitial_ok(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Pruebas Inciales OK", text="Pruebas Iniciales OK", value="T-Initial-OK"
            ),
        ]

        await self._send_select_card_confirm_TInitial_ok(turn_context, buttons)

    async def _send_select_card_confirm_TInitial_ok(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Pruebas Iniciales OK?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 4. FOLLOW JENKINS JOB STATUS EN DRS
    async def _send_card_follow_job_status_drs(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Estado del job", text="Estado del job", value="JOB-Status"
            ),
        ]

        await self._send_select_card_follow_job_status_drs(turn_context, buttons)

    async def _send_select_card_follow_job_status_drs(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Seguir el estado del job en DRS?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 4. FOLLOW JENKINS JOB STATUS EN PROD
    async def _send_card_follow_job_status_prod(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Estado del job", text="Estado del job", value="PROD-JOB"
            ),
        ]

        await self._send_select_card_follow_job_status_prod(turn_context, buttons)

    async def _send_select_card_follow_job_status_prod(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Seguir el estado del job en PROD?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 2. TESTS OR ROLLBACK CARD

    async def _send_card_T_RB(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Tests DRS", text="Tests DRS", value="TESTS-Proceed"
            ),
            CardAction(
                type=ActionTypes.im_back, title="RollBack", text="RollBack", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_T_RB(turn_context, buttons)

    async def _send_select_card_T_RB(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Continuar con Tests DRS o RollBack?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 3. CONFIRM POST TESTS DRS OK

    async def _send_card_post_tests(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Tests OK", text="OK", value="T-Post-OK"
            ),
            CardAction(
                type=ActionTypes.im_back, title="Tests NO OK", text="NO OK", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_post_tests(turn_context, buttons)

    async def _send_select_card_post_tests(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Pruebas en DRS posteriores al deploy OK, o iniciar ROLLBACK?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

# 3. DRS OR ROLLBACK CARD

    async def _send_card_PROD_RB(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Prod", text="Prod", value="PROD-Proceed"
            ),
            CardAction(
                type=ActionTypes.im_back, title="RollBack", text="RollBack", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_PROD_RB(turn_context, buttons)

    async def _send_select_card_PROD_RB(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Continuar a PROD o RollBack?", text="", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )


# 3. CONFIRM POST TESTS DRS OK

    async def _send_card_post_tests_prod(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.im_back, title="Tests PROD OK", text="OK", value="T-Prod-OK"
            ),
            CardAction(
                type=ActionTypes.im_back, title="Tests PROD NO OK", text="NO OK", value="RB-Proceed"
            ),
        ]

        await self._send_select_card_post_tests_prod(turn_context, buttons)

    async def _send_select_card_post_tests_prod(self, turn_context: TurnContext, buttons):
        card = HeroCard(
            title="Pruebas en PROD posteriores al deploy OK, o iniciar ROLLBACK?", text="", buttons=buttons
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

# 5. CONFIRMATION OF ACTIONS

# en esta seccion estan todas las confirmaciones de la accion a ejecutar

# a) se solicita confirmacion OK de las pruebas iniciales

    async def _confirmPrevious(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_initial_tests = MessageFactory.text(
            f"{mention.text} Control de red, confirme realizacion Ok de pruebas iniciales")
        reply_activity_initial_tests.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_initial_tests)
        await self._send_card_confirm_TInitial_ok(turn_context, False)


# b) se confirma al streamer que puede proceder con el deploy de la CRQ ingresada


    async def _confirmDeploy(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_deploy = MessageFactory.text(
            f"{mention.text} Streamer, se puede iniciar el deploy de la CRQ ingresada")
        reply_activity_deploy.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_deploy)
        await self._send_card_follow_job_status_drs(turn_context, False)

# c) se confirma el inicio de deploy en DRS

    async def _confirmDRS(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_DRS = MessageFactory.text(
            f"{mention.text} Streamer, se confirma inicio del deploy en DRS")
        reply_activity_DRS.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_DRS)


# e) se sollicita confirmacion a control de red que todo este OK en DRS


    async def _ask_control_confirmTests(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_TESTS_post = MessageFactory.text(
            f"{mention.text} Control de red, por favor confirme correcto funcionamiento posterior en DRS")
        reply_activity_TESTS_post.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_TESTS_post)

# f) se envia confirmacion de todo OK al streamer

    async def _communicate_control_postTests_OK(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_confirm_TESTS_post = MessageFactory.text(
            f"{mention.text} Streamer, se confirma correcto funcionamiento posterior DRS ")
        reply_activity_confirm_TESTS_post.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_confirm_TESTS_post)

# consultar a sistemas si se puede pasar a produccion
    async def _ask_PROD(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_confirm_prod_proceed = MessageFactory.text(
            f"{mention.text} Sistemas, se solicita confirmacion de paso a PROD")
        reply_activity_confirm_prod_proceed.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_confirm_prod_proceed)
        await self._send_card_PROD_RB(turn_context, False)

# g) se confirma paso a produccion

    async def _confirmProd(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_confirm_TESTS_post = MessageFactory.text(
            f"{mention.text} Streamer, se confirma paso a producción")
        reply_activity_confirm_TESTS_post.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_confirm_TESTS_post)

# e) se sollicita confirmacion a control de red que todo este OK en DRS

    async def _ask_control_confirmProdTests(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_TESTS_post = MessageFactory.text(
            f"{mention.text} Control de red, por favor confirme correcto funcionamiento posterior en PROD")
        reply_activity_TESTS_post.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_TESTS_post)

# f) se envia confirmacion de roll back al streamer

    async def _confirmRollback(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_RB = MessageFactory.text(
            f"{mention.text} Streamer, se confirma inicio de Rollback")
        reply_activity_RB.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_RB)

# g) se envia confirmacion cierre de deployment

    async def _confirmFinish(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_DP = MessageFactory.text(
            f"{mention.text} Sistemas, por favor, confirmar la finalización del deploy ")
        reply_activity_DP.entities = [
            Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity_DP)


# g) se envia confirmacion cierre de deployment


    async def _communicate_finish_deploy_streamer(self, turn_context: TurnContext):
        userAllowed = await self._get_users_allowed(turn_context)
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{userAllowed}</at>",
            type="mention",
        )

        reply_activity_DP = MessageFactory.text(
            f"{mention.text} Streamer, se confirma cierre del deploy de la CRQ por parte de Sistemas")
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
                )  
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
                    f"{member.name}. Se inician las pruebas en DRS."
                )
            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

# 3. MESSAGE ALL MEMBERS DRS

    async def _message_all_members_Prod(self, turn_context: TurnContext):
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
                    f"{member.name}. Inicio de deploy en PROD."
                )  
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
                ) 
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
                ) 
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
