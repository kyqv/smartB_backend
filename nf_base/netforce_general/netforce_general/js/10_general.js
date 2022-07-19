function check_action(action,context) {
    if (!context) context={};
    if (action.type=="post") return true;
    if (action.name=="login" || action.name=="manage_db" || action.name=="create_db" || action.name=="copy_db" || action.name=="upgrade_db" || action.name=="delete_db" || action.name=="nfw_trial_form_pre" || action.name=="forgot_passwd" || action.name=="forgot_passwd_done" || action.name=="change_passwd") return true;
    if (!context.user_id) {
        exec_action({name:"login"});
        return false;
    }
    return true;
}
