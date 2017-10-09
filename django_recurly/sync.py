
import recurly


from .models import logger, Account, BillingInfo




def modelify(resource, model_class, existing_instance=None, remove_empty=False, presave_callback=None):
    """
    Convert recurly resource objects to django models, by creating new instances or updating existing ones.

    Saves immediately the models created/updated.
    """

    __old = '''Modelify handles the dirty work of converting Recurly Resource objects to
    Django model instances, including resolving any additional Resource objects
    required to satisfy foreign key relationships. This method will query for
    existing instances based on unique model fields, or return a new instance if
    there is no match. Modelify does not save any models back to the database,
    it is left up to the application logic to decide when to do that.'''

    sentinel = object()

    # maps substructures of recurly records to corresponding django models
    SUBMODEL_MAPPER = {
        #'account': Account,
        'billing_info': BillingInfo,
        #'subscription': Subscription,
        #'transaction': Payment,
    }

    UNTOUCHABLE_MODEL_FIELDS = ["id", "user", "account"] + list(SUBMODEL_MAPPER.keys())  # pk and foreign keys
    EXTRA_ATTRIBUTES = ("hosted_login_token", "state", "closed_at")  # missing in resource.attributes
    model_fields_by_name = dict((field.name, field) for field in model_class._meta.fields
                                if field.name not in UNTOUCHABLE_MODEL_FIELDS)
    model_fields = set(model_fields_by_name.keys())

    # we ensure that missing attributes of xml payload don't lead to bad overrides of model fields
    # some values may be present and None though, due to nil="nil" xml attribute
    remote_data = {key: getattr(resource, key, sentinel) for key in resource.attributes + EXTRA_ATTRIBUTES}
    remote_data = {key: value for (key, value) in remote_data.items() if value is not sentinel}

    logger.debug("Modelify %s record input: %s", resource.nodename, remote_data)

    '''
    for k, v in data.copy().items():

        # FIXME - still useful ???
        # Expand 'uuid' to work with payment notifications and transaction API queries
        if k == 'uuid' and hasattr(resource, 'nodename') and not hasattr(data, resource.nodename + '_id'):
            data[resource.nodename + '_id'] = v

        # Recursively replace links to known keys with actual models
        # TODO: (IW) Check that all expected foreign keys are mapped
        if k in MODEL_MAP and k in fields:
            if k in context:
                logger.debug("Using provided context object for: %s", k)
                data[k] = context[k]
            elif not k in follow:
                logger.debug("Not following linked: %s", k)
                del data[k]
                continue

            logger.debug("Following linked: %s", k)
            if isinstance(v, str):
                try:
                    v = resource.link(k)
                except AttributeError:
                    pass

            if callable(v):  # ??? when ???
                v = v()

            logger.debug("Modelifying nested: %s", k)
            # TODO: (IW) This won't attach foreign keys for reverse lookups
            # e.g. account has no attribute 'billing_info'
            data[k] = modelify(v, MODEL_MAP[k], remove_empty=remove_empty, follow=follow, context=context)
    '''


    model_updates = {}

    for k, v in remote_data.items():

        if k not in model_fields:
            continue  # data not mirrored in SQL DB

        # Fields with limited choices should always be lower case
        if v and model_fields_by_name[k].choices:
            v = v.lower()  # this shall be a string

        if v or not remove_empty:
            model_updates[k] = v

    logger.debug("Modelify %s model pending updates: %s", resource.nodename, model_updates)

    # Check for existing model object with the same unique field (account_code, uuid...)

    if existing_instance:
        logger.debug("Using already provided %s instance with id=%s for update",
                     model_class.__name__, existing_instance.pk)

    elif model_class.UNIQUE_LOOKUP_FIELD:

        if not model_updates.get(model_class.UNIQUE_LOOKUP_FIELD):
            raise RuntimeError("Remote recurly record has no value for unique field %s" %
                                 model_class.UNIQUE_LOOKUP_FIELD)

        unique_field_filter = {model_class.UNIQUE_LOOKUP_FIELD:
                               model_updates[model_class.UNIQUE_LOOKUP_FIELD]}

        try:
            existing_instance = model_class.objects.get(**unique_field_filter)
            logger.debug("Found existing %s instance id=%s matching remote recurly data",
                         model_class.__name__, existing_instance.pk)
        except model_class.DoesNotExist:
            logger.debug("No %s instance found matching unique field filter '%s', returning new object",
                         model_class.__name__, unique_field_filter)

    else:
        pass  # eg. case of a billing_info not existing locally yet

    if existing_instance:
        # Update fields of existing object (even with None values)
        obj = existing_instance
        for k, v in model_updates.items():
            setattr(obj, k, v)
    else:
        # Create a new model instance
        obj = model_class(**model_updates)

    if presave_callback:
        presave_callback(obj)
    obj.save()  # sets primary key if not present

    for (relation, subsinstance_klass) in SUBMODEL_MAPPER.items():

        if not hasattr(model_class, relation):
            continue  # this model doesn't contain such a relation

        is_one_to_one_relation = not relation.endswith("s")  # quick and dirty
        if is_one_to_one_relation:
            def _new_presave_callback(_subobj):
                setattr(obj, relation, _subobj)
        else:
            # it's a pool of related objects like "subscriptions"...
            def _new_presave_callback(_subobj):
                rels = getattr(obj, relation)
                rels.add(_subobj)

        local_instance = getattr(obj, relation, None)

        logger.debug("LOOOOOOOOKUUING UP RESOURCE EXTRACT %s %s %s", resource, relation, resource.__dict__)
        remote_resource = getattr(resource, relation, None)
        #logger.debug("Remote_resource _elem: %s", remote_resource._elem)

        if remote_resource:
            # we create or override sub-instance
            subobj = modelify(remote_resource, subsinstance_klass,
                              existing_instance=local_instance,
                              presave_callback=_new_presave_callback)
            setattr(obj, relation, subobj)
        else:
            assert not remote_resource
            if local_instance:
                local_instance.delete()  # delete obsolete instance
                setattr(obj, relation, None)  # security
            else:
                pass  # both unexisting, it's OK

    return obj






def update_local_account_data_from_recurly_resource(recurly_account=None,
                                                    account_code=None):
    """
    Overrides local Account and BillingInfo fields with remote ones.
    """

    cls = Account

    if recurly_account is None:
        assert account_code
        recurly_account = recurly.Account.get(account_code)
    assert isinstance(recurly_account, recurly.Account)

    logger.debug("Account.update_local_data_from_recurly_resource for %s", recurly_account.account_code)
    account = modelify(recurly_account, cls)
    ## useless account.save()

    ''' NOPE
    # Update billing info from nested account data
    if hasattr(recurly_account, "billing_info"):
        BillingInfo.update_local_data_from_recurly_resource(
            recurly_billing_info=recurly_account.billing_info
        )
    else:
        BillingInfo.update_local_data_from_recurly_resource(account_code=account.account_code)
        '''
    return account



# FIXME - UNUSED ???
def ______update_local_billing_info_data_from_recurly_resource(recurly_billing_info):

    cls = BillingInfo

    logger.debug("BillingInfo.sync: %s", recurly_billing_info)
    billing_info = modelify(recurly_billing_info, cls)

    if hasattr(billing_info, 'account') and not billing_info.account.pk:
        billing_info.account.save(remote=False)
        billing_info.account_id = billing_info.account.pk

    billing_info.save(remote=False)
    return billing_info
