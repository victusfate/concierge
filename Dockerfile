FROM victusfate/concierge_requirements
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /var/www/concierge
COPY . /var/www/concierge
RUN make clean
RUN make dependencies
RUN make application
EXPOSE 5000

ENV PYTHONPATH='/var/www/concierge/:$PYTHONPATH'

CMD ["/var/www/concierge/entrypoint.sh"]
# ENTRYPOINT ["/var/www/concierge/entrypoint.sh"]

