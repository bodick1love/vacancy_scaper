import os
import json
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    filters,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import models
from parsers import WorkUaParser
from parsers import RobotaUaParser


logger = logging.getLogger(__name__)


class TelegramResumeBot:
    """
    A Telegram bot for searching resumes across multiple job websites (Work.ua, Robota.ua)
    based on user-provided parameters like keywords, region, salary, and experience.

    Attributes:
        work_ua_parser (WorkUaParser): A parser for interacting with the Work.ua website.
        robota_ua_parser (RobotaUaParser): A parser for interacting with the Robota.ua website.
        __application (ApplicationBuilder): A Telegram bot application instance.
        __user_data (dict): Stores user-specific data, including search options and state.
        SALARY_FROM_OPTIONS (dict): Salary options for filtering results (minimum salary).
        SALARY_TO_OPTIONS (dict): Salary options for filtering results (maximum salary).
        EXPERIENCE_OPTIONS (dict): Experience options for filtering search results.
    """

    def __init__(self, work_ua_parser: WorkUaParser, robota_ua_parser: RobotaUaParser):
        """
        Initializes the TelegramResumeBot with parsers for Work.ua and Robota.ua, sets up the
        bot application, and loads salary and experience options from JSON files.

        Args:
            work_ua_parser (WorkUaParser): A parser for Work.ua.
            robota_ua_parser (RobotaUaParser): A parser for Robota.ua.
        """

        self.work_ua_parser = work_ua_parser
        self.robota_ua_parser = robota_ua_parser
        self.__application = (
            ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
        )
        self.__user_data = {}
        self.__load_salary_options()
        self.__load_experience_options()

    def __load_salary_options(self) -> None:
        """
        Loads salary options from a JSON file specified by the environment variable
        TELEGRAM_SALARY_OPTIONS_JSON_PATH. If the file cannot be read or parsed, logs an error.
        """
        json_file_path = os.getenv("TELEGRAM_SALARY_OPTIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                salary_options = json.load(json_file)
                self.SALARY_FROM_OPTIONS = salary_options["SALARY_FROM_OPTIONS"]
                self.SALARY_TO_OPTIONS = salary_options["SALARY_TO_OPTIONS"]
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load salary options from file: {e}.")
            return

    def __load_experience_options(self) -> None:
        """
        Loads experience options from a JSON file specified by the environment variable
        TELEGRAM_EXPERIENCE_OPTIONS_JSON_PATH. If the file cannot be read or parsed, logs an error.
        """
        json_file_path = os.getenv("TELEGRAM_EXPERIENCE_OPTIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                experience_options = json.load(json_file)
                self.EXPERIENCE_OPTIONS = experience_options
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load experience options from file: {e}.")
            return

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Starts the interaction with the user, welcoming them and providing a menu of available commands.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        self.__user_data[update.effective_chat.id] = {
            "state": models.UserState.FREE,
            "search_options": {
                "search": "",
                "region": "",
                "salary_from": 0,
                "salary_to": 0,
                "experience": [],
            },
        }

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Hello! I'm a bot and I can find suiting resumes according to parameters you've provided.\n"
                "Choose your option:\n"
                "/keywords - search query\n"
                "/region - region\n"
                "/salary - salary range\n"
                "/experience - required experience\n"
                "/search - start searching\n"
                "/clear - clear all parameters"
            ),
        )

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Stops the bot interaction for the current user, clearing their data.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        self.__user_data.pop(update.effective_chat.id)

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Goodbye! Hope I was helpful."
        )

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Clears the user's search parameters and restores them to default values.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id
        self.__user_data[chat_id] = {
            "state": models.UserState.FREE,
            "search_options": {
                "search": "",
                "region": "",
                "salary_from": "",
                "salary_to": "",
                "experience": [],
            },
        }
        await context.bot.send_message(
            chat_id=chat_id,
            text="All parameters cleared. Now you can provide new parameters.",
        )

    async def set_parameter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles setting a user parameter (keywords, region).

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id
        text = update.message.text

        if text.startswith("/keywords"):
            await context.bot.send_message(
                chat_id=chat_id, text="Please provide your search query."
            )
            self.__user_data[chat_id]["state"] = models.UserState.ASKING_KEYWORDS

        elif text.startswith("/region"):
            await context.bot.send_message(
                chat_id=chat_id, text="Please provide your desired region."
            )
            self.__user_data[chat_id]["state"] = models.UserState.ASKING_REGION

    async def accept_parameter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Accepts a parameter provided by the user and updates their search options.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id
        text = update.message.text

        if not self.__user_data.get(chat_id):
            await context.bot.send_message(
                chat_id=chat_id, text="Please type /start to make some request."
            )
            return

        if self.__user_data[chat_id]["state"] == models.UserState.FREE:
            await context.bot.send_message(
                chat_id=chat_id,
                text="It seems like you're not choosing any parameter, type one of provided commands:"
                "/keywords, "
                "/region, "
                "/salary, "
                "/experience, "
                "/search, "
                "/clear",
            )
        elif self.__user_data[chat_id]["state"] == models.UserState.ASKING_KEYWORDS:
            self.__user_data[chat_id]["search_options"]["search"] = text
            await context.bot.send_message(
                chat_id=chat_id, text=f"Search query set to: {text}"
            )

        elif self.__user_data[chat_id]["state"] == models.UserState.ASKING_REGION:
            self.__user_data[chat_id]["search_options"]["region"] = text
            await context.bot.send_message(
                chat_id=chat_id, text=f"Region set to: {text}"
            )

        self.__user_data[chat_id]["state"] = models.UserState.FREE

    def __get_experience_mapping(self) -> dict:
        """
        Maps the experience labels to their corresponding keys.

        Returns:
            dict: A mapping of experience labels to their keys.
        """
        return {label: key for key, label in self.EXPERIENCE_OPTIONS.items()}

    def __build_experience_keyboard(
        self, selected_experience: list
    ) -> InlineKeyboardMarkup:
        """
        Builds an inline keyboard for selecting experience levels.

        Args:
            selected_experience (list): The list of selected experience levels.

        Returns:
            InlineKeyboardMarkup: The inline keyboard markup.
        """
        experience_mapping = self.__get_experience_mapping()

        keyboard = []
        for key, label in experience_mapping.items():
            if label in selected_experience:
                keyboard.append(
                    [InlineKeyboardButton(f"✅ {label}", callback_data=key)]
                )  # Checked
            else:
                keyboard.append(
                    [InlineKeyboardButton(label, callback_data=key)]
                )  # Unchecked

        keyboard.extend(
            [
                [
                    InlineKeyboardButton("🔄 Reset", callback_data="experience_reset"),
                    InlineKeyboardButton(
                        "✔️ Complete", callback_data="experience_complete"
                    ),
                ],
            ]
        )
        return InlineKeyboardMarkup(keyboard)

    async def experience(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles the user request to set the experience level parameter.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id

        reply_markup = self.__build_experience_keyboard(
            self.__user_data[chat_id]["search_options"]["experience"]
        )

        self.__user_data[chat_id]["state"] = models.UserState.ASKING_EXPERIENCE

        await context.bot.send_message(
            chat_id=chat_id,
            text="Please choose your experience levels (you can select multiple):",
            reply_markup=reply_markup,
        )

    async def experience_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles the callback for selecting or deselecting experience options in the user's search query.
        This function processes the user's experience selections, updates the selection, and allows for resetting or completing the experience selection.

        Args:
            update (Update): The incoming callback query containing information about the user's choice.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        user_data = self.__user_data[chat_id]
        selected_experience = user_data["search_options"].get("experience", [])

        experience_mapping = self.__get_experience_mapping()

        if query.data == "experience_complete":
            selected_text = (
                ", ".join(selected_experience) if selected_experience else "None"
            )
            user_data["state"] = models.UserState.FREE
            await query.edit_message_text(
                text=f"Experience selection completed: {selected_text}."
            )

            self.__user_data[chat_id]["state"] = models.UserState.FREE
            return

        if query.data == "experience_reset":
            user_data["search_options"]["experience"] = []
            await query.edit_message_text(
                text="Experience options have been reset. Please select again.",
                reply_markup=self.__build_experience_keyboard(selected_experience),
            )
            return

        selected_option = experience_mapping[query.data]
        if selected_option in selected_experience:
            selected_experience.remove(selected_option)
        else:
            selected_experience.append(selected_option)

        await query.edit_message_text(
            text=f"Experience options selected: {', '.join(selected_experience) if selected_experience else 'None'}\n"
            "You can toggle options, reset, or complete your selection.",
            reply_markup=self.__build_experience_keyboard(selected_experience),
        )

    async def search_resumes(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Searches resumes based on the user's parameters (keywords, region, salary, experience).
        Combines results from multiple job websites (Work.ua, Robota.ua), sorts them, and sends
        the top 5 resumes to the user.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id
        search_options = self.__user_data[chat_id]["search_options"]

        logger.info(search_options)

        if "search" not in search_options:
            await context.bot.send_message(
                chat_id=chat_id, text="Please provide at least keywords."
            )
            return

        search_options = models.SearchOptions(**search_options)

        work_ua_results = self.work_ua_parser.search_resumes(search_options.copy())
        robota_ua_results = self.robota_ua_parser.search_resumes(search_options.copy())

        combined_results = work_ua_results + robota_ua_results
        combined_results.sort(reverse=True)
        top_resumes = combined_results[:5]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Found {len(combined_results)} resumes\n"
            f"You can see top 5 below:\n"
            f"{"\n".join([TelegramResumeBot.format_resume(resume) for resume in top_resumes])}",
        )

    async def salary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Initiates the salary parameter selection by sending an inline keyboard with salary options.
        The user is asked to select the minimum salary.

        Args:
            update (Update): The incoming update containing information about the message.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        chat_id = update.effective_chat.id
        self.__user_data[chat_id]["state"] = models.UserState.ASKING_SALARY_FROM

        keyboard = [
            [InlineKeyboardButton(label, callback_data=f"salary_from:{value}")]
            for label, value in self.SALARY_FROM_OPTIONS.items()
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text="Select the minimum salary:",
            reply_markup=reply_markup,
        )

    async def salary_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles the callback for selecting the minimum or maximum salary in the user's search query.
        The user selects either the minimum or maximum salary, and the bot updates the salary parameters.

        Args:
            update (Update): The incoming callback query containing information about the user's choice.
            context (ContextTypes.DEFAULT_TYPE): The context for the bot interaction.
        """
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        data = query.data

        if data.startswith("salary_from:"):
            self.__user_data[chat_id]["search_options"]["salary_from"] = int(
                data.split(":")[1]
            )
            self.__user_data[chat_id]["state"] = models.UserState.ASKING_SALARY_TO

            keyboard = [
                [InlineKeyboardButton(label, callback_data=f"salary_to:{value}")]
                for label, value in self.SALARY_TO_OPTIONS.items()
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text="Select the maximum salary:", reply_markup=reply_markup
            )

        elif data.startswith("salary_to:"):
            self.__user_data[chat_id]["search_options"]["salary_to"] = int(
                data.split(":")[1]
            )
            self.__user_data[chat_id]["state"] = models.UserState.FREE

            await query.edit_message_text(text="Salary range set successfully.")

    @staticmethod
    def format_resume(resume: models.Resume) -> str:
        """
        Formats a resume object into a human-readable string.

        Args:
            resume (models.Resume): The resume object containing the resume details.

        Returns:
            str: The formatted resume string, including links, salary, experience, and filling percentage.
        """
        formatted_resume = f"Resume: {resume.href}\n"

        if resume.salary_expectation:
            formatted_resume += f"Salary expectation: {resume.salary_expectation}\n"

        if resume.experience:
            formatted_resume += "Experience/Education:\n"
            for exp in resume.experience:
                formatted_resume += f"    Position: {exp.position or 'N/A'}\n"
                formatted_resume += f"    Duration: {exp.duration or 'N/A'}\n"
                formatted_resume += f"    Details: {exp.details or 'N/A'}\n\n"

        formatted_resume += f"Resume filling percentage: {resume.filling_percentage}%\n"

        return formatted_resume

    def run(self):
        """
        Starts the bot and sets up all the necessary command and callback handlers for user interactions.
        The bot will run and listen for user commands, handling their requests accordingly.

        This function adds handlers for starting, stopping, clearing parameters, setting parameters,
        searching resumes, handling salary and experience selection, and more.
        """
        start_handler = CommandHandler("start", self.start)
        stop_handler = CommandHandler("stop", self.stop)
        clear_handler = CommandHandler("clear", self.clear)
        set_param_handler = CommandHandler(["keywords", "region"], self.set_parameter)

        experience_handler = CommandHandler("experience", self.experience)
        experience_callback_handler = CallbackQueryHandler(
            self.experience_callback, pattern="^experience_"
        )

        salary_handler = CommandHandler("salary", self.salary)
        salary_callback_handler = CallbackQueryHandler(
            self.salary_callback, pattern="^salary_(from|to):"
        )

        search_handler = CommandHandler("search", self.search_resumes)
        accept_parameter_handler = MessageHandler(
            filters.TEXT & (~filters.COMMAND), self.accept_parameter
        )

        self.__application.add_handler(start_handler)
        self.__application.add_handler(stop_handler)
        self.__application.add_handler(clear_handler)
        self.__application.add_handler(set_param_handler)
        self.__application.add_handler(experience_handler)
        self.__application.add_handler(experience_callback_handler)
        self.__application.add_handler(salary_handler)
        self.__application.add_handler(salary_callback_handler)
        self.__application.add_handler(search_handler)
        self.__application.add_handler(accept_parameter_handler)

        self.__application.run_polling()
